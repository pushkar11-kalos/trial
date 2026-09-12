"""Selects the configured OCR provider (see .env / OCR_PROVIDER)."""
from ...config import settings
from .base import OCRProvider
from .mock_provider import MockOCRProvider


def get_ocr_provider() -> OCRProvider:
    if settings.OCR_PROVIDER == "gemini":
        from .gemini_provider import GeminiOCRProvider

        return GeminiOCRProvider()
    if settings.OCR_PROVIDER == "tesseract":
        from .tesseract_provider import TesseractOCRProvider

        return TesseractOCRProvider()
    return MockOCRProvider()
