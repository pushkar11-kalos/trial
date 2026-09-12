"""
MockOCRProvider -- makes DEMO MODE work with zero external services or API
keys, and is also the default provider (`OCR_PROVIDER=mock`) because it's
the most reliable option for a hackathon judge running this cold.

Three tiers, tried in order:
  1. Canned lookup for the 3 seeded demo scenarios (deterministic --
     the hackathon walkthrough must reproduce the same result every time).
  2. A best-effort *real* OCR pass via pytesseract, IF the tesseract binary
     happens to be present in this environment. This means MetraCheck can
     still genuinely OCR an officer's own uploaded photo even while
     OCR_PROVIDER=mock, whenever the environment supports it.
  3. An honest "manual entry required" result (confidence 0) if neither
     applies. We never fabricate OCR text for a real, non-demo image.
"""
import logging
from typing import Optional

from ...seed_data.demo_scenarios import SCENARIOS
from .base import OCRBlock, OCRProvider, OCRResult

logger = logging.getLogger(__name__)


def _build_canned_result(scenario_key: str, slug: str) -> Optional[OCRResult]:
    scenario = SCENARIOS.get(scenario_key)
    if not scenario:
        return None
    spec = next((s for s in scenario.images if s.slug == slug), None)
    if not spec:
        return None

    n = len(spec.lines)
    blocks = []
    for i, line in enumerate(spec.lines):
        band_h = 1.0 / (n + 1)
        blocks.append(
            OCRBlock(
                text=line.text,
                bbox=[0.06, round((i + 0.5) * band_h, 4), 0.88, round(band_h * 0.8, 4)],
                confidence=line.confidence,
            )
        )
    return OCRResult(
        engine_name="mock (demo dataset)",
        raw_text=spec.full_text,
        blocks=blocks,
        overall_confidence=spec.overall_confidence,
        requires_manual_entry=False,
        warnings=(
            ["Simulated reduced-quality capture — see individual field confidences."]
            if spec.blurred
            else []
        ),
    )


def _try_real_tesseract(image_path: str) -> Optional[OCRResult]:
    try:
        from .tesseract_provider import TesseractOCRProvider

        return TesseractOCRProvider().process(image_path)
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.info("Tesseract fallback unavailable (%s); using manual-entry result.", exc)
        return None


class MockOCRProvider(OCRProvider):
    def process(self, image_path: str, demo_key: Optional[str] = None) -> OCRResult:
        if demo_key and ":" in demo_key:
            scenario_key, slug = demo_key.split(":", 1)
            canned = _build_canned_result(scenario_key, slug)
            if canned:
                return canned

        real = _try_real_tesseract(image_path)
        if real is not None:
            real.engine_name = f"{real.engine_name} (mock auto-fallback)"
            return real

        return OCRResult(
            engine_name="mock (no engine available)",
            raw_text="",
            blocks=[],
            overall_confidence=0.0,
            requires_manual_entry=True,
            warnings=[
                "Automatic text extraction was not available for this image in this "
                "environment. Enter the label text manually below — manually entered "
                "text is clearly labelled as such throughout the inspection."
            ],
        )
