"""
Gemini Vision OCR provider -- uses Google Gemini API for high-accuracy
text extraction from photographed product labels.

Requires GEMINI_API_KEY to be set. Uses gemini-2.0-flash by default
(configurable via GEMINI_MODEL).

When a demo_key is provided, delegates to the mock provider's canned
lookup so demo mode remains deterministic.
"""
import base64
import json
import logging
from pathlib import Path
from typing import Optional

from ...config import settings
from .base import OCRBlock, OCRProvider, OCRResult
from .mock_provider import MockOCRProvider

logger = logging.getLogger(__name__)

_OCR_PROMPT = """\
You are an OCR engine for Indian product packaging / legal metrology labels.

Return a JSON object with exactly these keys:
{
  "raw_text": "<full transcription of all visible text, line by line>",
  "blocks": [
    {
      "text": "<one logical line or phrase>",
      "confidence": <0-100 integer, your estimate of transcription accuracy>
    }
  ]
}

Rules:
- Each "block" is one logical line or phrase visible on the label.
- Group related short fragments (e.g. "MRP Rs." and "199.00") into one block.
- confidence: 95+ for clear text, 80-94 for slightly blurred/small text, 60-79 for partially occluded, below 60 for barely readable.
- Do NOT fabricate text. Only transcribe what you can actually see.
- Preserve original casing, spacing, and line breaks as closely as possible.
- Return ONLY the JSON object, no markdown fences, no commentary."""


class GeminiOCRProvider(OCRProvider):
    """OCR via Google Gemini Vision API."""

    def process(self, image_path: str, demo_key: Optional[str] = None) -> OCRResult:
        # For demo keys, use canned data so demo mode stays deterministic
        if demo_key and ":" in demo_key:
            try:
                mock = MockOCRProvider()
                return mock.process(image_path, demo_key=demo_key)
            except Exception:
                pass  # fall through to real Gemini call

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return OCRResult(
                engine_name="gemini (no API key)",
                raw_text="",
                blocks=[],
                overall_confidence=0.0,
                requires_manual_entry=True,
                warnings=["GEMINI_API_KEY is not configured. Enter label text manually."],
            )

        try:
            import google.generativeai as genai
        except ImportError:
            return OCRResult(
                engine_name="gemini (SDK not installed)",
                raw_text="",
                blocks=[],
                overall_confidence=0.0,
                requires_manual_entry=True,
                warnings=[
                    "google-generativeai package is not installed. "
                    "Run: pip install google-generativeai"
                ],
            )

        try:
            return self._call_gemini(genai, api_key, image_path)
        except Exception as exc:
            logger.exception("Gemini OCR call failed")
            return OCRResult(
                engine_name="gemini (error)",
                raw_text="",
                blocks=[],
                overall_confidence=0.0,
                requires_manual_entry=True,
                warnings=[f"Gemini API error: {exc}. Enter label text manually."],
            )

    def _call_gemini(self, genai, api_key: str, image_path: str) -> OCRResult:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        image_bytes = Path(image_path).read_bytes()
        mime = "image/jpeg"
        lower = image_path.lower()
        if lower.endswith(".png"):
            mime = "image/png"
        elif lower.endswith(".webp"):
            mime = "image/webp"
        elif lower.endswith(".gif"):
            mime = "image/gif"

        image_part = {"mime_type": mime, "data": image_bytes}

        response = model.generate_content(
            [image_part, _OCR_PROMPT],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )

        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Gemini returned non-JSON response, treating raw text as OCR output")
            return OCRResult(
                engine_name="gemini",
                raw_text=text,
                blocks=[OCRBlock(text=line.strip(), bbox=[0.0, 0.0, 1.0, 1.0 / max(text.count("\n") + 1, 1)], confidence=85.0) for line in text.splitlines() if line.strip()],
                overall_confidence=80.0,
                requires_manual_entry=False,
                warnings=["Gemini response was not valid JSON; raw text was used."],
            )

        raw_text = data.get("raw_text", "")
        raw_blocks = data.get("blocks", [])

        blocks: list[OCRBlock] = []
        confidences: list[float] = []
        n = len(raw_blocks)
        for i, b in enumerate(raw_blocks):
            btext = (b.get("text") or "").strip()
            if not btext:
                continue
            conf = float(b.get("confidence", 85))
            band_h = 1.0 / max(n, 1)
            blocks.append(
                OCRBlock(
                    text=btext,
                    bbox=[0.05, round((i + 0.5) * band_h, 4), 0.9, round(band_h * 0.8, 4)],
                    confidence=conf,
                )
            )
            confidences.append(conf)

        overall = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        warnings: list[str] = []
        if overall < settings.OCR_REVIEW_CONFIDENCE_THRESHOLD:
            warnings.append(
                f"Gemini overall confidence ({overall:.0f}%) is below the "
                f"{settings.OCR_REVIEW_CONFIDENCE_THRESHOLD}% threshold -- "
                f"please visually verify against the evidence image."
            )

        return OCRResult(
            engine_name="gemini",
            raw_text=raw_text,
            blocks=blocks,
            overall_confidence=overall,
            requires_manual_entry=(len(blocks) == 0),
            warnings=warnings,
        )
