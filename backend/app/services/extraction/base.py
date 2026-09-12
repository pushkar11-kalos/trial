"""Declaration extraction abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ..ocr.base import OCRBlock
from ...models import DeclarationField


@dataclass
class EvidenceOCRInput:
    """One evidence image's OCR blocks, tagged with its evidence_id."""
    evidence_id: int
    blocks: List[OCRBlock]


@dataclass
class ExtractedField:
    field_key: DeclarationField
    value: str
    confidence: float
    source_evidence_id: Optional[int]
    bounding_box: Optional[List[float]]
    extraction_method: str


class DeclarationExtractor(ABC):
    @abstractmethod
    def extract(
        self, evidence_inputs: List[EvidenceOCRInput], product_brand: str
    ) -> List[ExtractedField]:
        raise NotImplementedError
