"""
OCR provider abstraction.

Every provider returns the same OCRResult shape regardless of engine, so
routers and the declaration extractor never need to know which one ran.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OCRBlock:
    text: str
    bbox: List[float]  # [x, y, w, h], normalized 0..1 relative to image size
    confidence: float  # 0-100


@dataclass
class OCRResult:
    engine_name: str
    raw_text: str
    blocks: List[OCRBlock] = field(default_factory=list)
    overall_confidence: float = 0.0
    requires_manual_entry: bool = False
    warnings: List[str] = field(default_factory=list)


class OCRProvider(ABC):
    @abstractmethod
    def process(self, image_path: str, demo_key: Optional[str] = None) -> OCRResult:
        """
        Run OCR on the image at image_path.

        demo_key, when provided, is an opaque identifier (e.g. the demo
        evidence's stored filename) that a provider MAY use to short-circuit
        to a deterministic canned result. Providers that don't recognize the
        key fall back to genuine processing.
        """
        raise NotImplementedError
