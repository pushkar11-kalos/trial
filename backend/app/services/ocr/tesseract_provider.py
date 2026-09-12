"""
Real OCR via pytesseract + the system `tesseract` binary, with light OpenCV
preprocessing when available. Used when OCR_PROVIDER=tesseract, and as a
best-effort fallback from MockOCRProvider for non-demo images.

Both `pytesseract`/the tesseract binary and `opencv-python-headless` are
optional at runtime: import failures are caught by the caller
(MockOCRProvider._try_real_tesseract) or surfaced clearly if this provider
is explicitly selected via OCR_PROVIDER=tesseract with the binary missing.
"""
from typing import Optional

from .base import OCRBlock, OCRProvider, OCRResult


def _preprocess(image_path: str) -> str:
    """
    Grayscale + adaptive threshold via OpenCV to improve OCR accuracy on
    photographed (as opposed to scanned) labels. Returns a path to the
    preprocessed image, or the original path if OpenCV isn't installed.
    """
    try:
        import cv2  # type: ignore
    except ImportError:
        return image_path

    img = cv2.imread(image_path)
    if img is None:
        return image_path
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    out_path = f"{image_path}.preprocessed.png"
    cv2.imwrite(out_path, thresh)
    return out_path


class TesseractOCRProvider(OCRProvider):
    def process(self, image_path: str, demo_key: Optional[str] = None) -> OCRResult:
        import pytesseract
        from PIL import Image

        processed_path = _preprocess(image_path)
        img = Image.open(processed_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        width, height = img.size
        blocks: list[OCRBlock] = []
        confidences: list[float] = []
        text_parts: list[str] = []

        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            conf_raw = data["conf"][i]
            try:
                conf = float(conf_raw)
            except (TypeError, ValueError):
                conf = -1.0
            if not text or conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            blocks.append(
                OCRBlock(
                    text=text,
                    bbox=[x / width, y / height, w / width, h / height],
                    confidence=conf,
                )
            )
            confidences.append(conf)
            text_parts.append(text)

        overall = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
        return OCRResult(
            engine_name="tesseract",
            raw_text="\n".join(text_parts),
            blocks=blocks,
            overall_confidence=overall,
            requires_manual_entry=(len(blocks) == 0),
            warnings=[] if blocks else ["Tesseract returned no recognizable text."],
        )
