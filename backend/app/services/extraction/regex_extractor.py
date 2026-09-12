"""
RegexDeclarationExtractor -- deterministic, keyword/regex-driven extraction
of structured declarations from raw OCR line text. No AI/LLM involved; this
is the extractor that runs by default and is what the rule engine consumes.

Field-detection strategy, per line, in order (first match wins per line):
  1. Manufacturer/packer/importer name  (keyword prefix)
  2. Country of origin                  (keyword prefix)
  3. Net quantity                       (keyword prefix)
  4. MRP                                (keyword prefix)
  5. Manufacturing/packing/import date  (keyword prefix)
  6. Best before / use by               (keyword prefix)
  7. Consumer/customer care             (keyword prefix)
  8. Unit sale price                    (keyword prefix)
  9. Positional fallback: the line immediately after a manufacturer-name
     match, if otherwise unclaimed, is treated as the address -- this
     mirrors how these two declarations are conventionally printed together
     on real packaging.
  10. Generic/common name fallback: the first still-unclaimed line, across
      all images, that isn't a substring match of the declared brand name
      (brand and generic name are conventionally on separate lines, brand
      usually first/largest).

Confidence on every extracted field is the OCR confidence of the line it
came from -- there is no separate "extraction confidence"; low-confidence
OCR flows straight through to a low-confidence declaration, which is what
lets the rule engine's confidence-downgrade mechanic work (see
app/services/rules/engine.py).
"""
import re
from typing import List, Optional

from ...models import DeclarationField
from .base import DeclarationExtractor, EvidenceOCRInput, ExtractedField

_PATTERNS: list[tuple[DeclarationField, re.Pattern]] = [
    (
        DeclarationField.MANUFACTURER_NAME,
        re.compile(
            r"^(Mfd\.?\s*by|Manufactured\s*by|Marketed\s*by|Packed\s*by|"
            r"Imported\s*&\s*Marketed\s*by|Imported\s*by)\s*[:\-]?\s*(?P<val>.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        DeclarationField.COUNTRY_OF_ORIGIN,
        re.compile(r"^Country\s*of\s*Origin\s*[:\-]?\s*(?P<val>.+)$", re.IGNORECASE),
    ),
    (
        DeclarationField.NET_QUANTITY,
        re.compile(
            r"^Net\s*(Wt\.?|Weight|Qty\.?|Quantity)\s*[:\-]?\s*(?P<val>.+)$", re.IGNORECASE
        ),
    ),
    (
        DeclarationField.MRP,
        re.compile(r"^MRP\s*[:\-]?\s*(?P<val>.+)$", re.IGNORECASE),
    ),
    (
        DeclarationField.MFG_DATE,
        re.compile(
            r"^(Mfd\.?|Manufactured|Pkd\.?|Packed|Imported)\s*(Date|On)\s*[:\-]?\s*(?P<val>.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        DeclarationField.BEST_BEFORE,
        re.compile(
            r"^(Best\s*Before|Use\s*By|Expiry|Exp\.?|BB)\s*[:\-]?\s*(?P<val>.+)$", re.IGNORECASE
        ),
    ),
    (
        DeclarationField.CONSUMER_CARE,
        re.compile(
            r"^(Consumer\s*Care|Customer\s*Care|Helpline|Contact)\s*[:\-]?\s*(?P<val>.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        DeclarationField.UNIT_SALE_PRICE,
        re.compile(r"^Unit\s*Sale\s*Price\s*[:\-]?\s*(?P<val>.+)$", re.IGNORECASE),
    ),
]


def _is_brand_line(text: str, brand: str) -> bool:
    if not brand:
        return False
    t, b = text.strip().upper(), brand.strip().upper()
    return bool(t) and bool(b) and (b in t or t in b)


class RegexDeclarationExtractor(DeclarationExtractor):
    def extract(
        self, evidence_inputs: List[EvidenceOCRInput], product_brand: str
    ) -> List[ExtractedField]:
        found: dict[DeclarationField, ExtractedField] = {}
        generic_name_candidate: Optional[ExtractedField] = None

        def maybe_store(field: ExtractedField) -> None:
            existing = found.get(field.field_key)
            if existing is None or field.confidence > existing.confidence:
                found[field.field_key] = field

        for evidence in evidence_inputs:
            prev_was_manufacturer = False
            for block in evidence.blocks:
                line = block.text.strip()
                if not line:
                    prev_was_manufacturer = False
                    continue

                matched = False
                for field_key, pattern in _PATTERNS:
                    m = pattern.match(line)
                    if m:
                        value = m.group("val").strip()
                        maybe_store(
                            ExtractedField(
                                field_key=field_key,
                                value=value,
                                confidence=block.confidence,
                                source_evidence_id=evidence.evidence_id,
                                bounding_box=block.bbox,
                                extraction_method=f"regex:{field_key.value}",
                            )
                        )
                        matched = True
                        prev_was_manufacturer = field_key == DeclarationField.MANUFACTURER_NAME
                        break

                if matched:
                    continue

                if prev_was_manufacturer and DeclarationField.ADDRESS not in found:
                    maybe_store(
                        ExtractedField(
                            field_key=DeclarationField.ADDRESS,
                            value=line,
                            confidence=block.confidence,
                            source_evidence_id=evidence.evidence_id,
                            bounding_box=block.bbox,
                            extraction_method="heuristic:address_after_manufacturer",
                        )
                    )
                    prev_was_manufacturer = False
                    continue

                prev_was_manufacturer = False

                if generic_name_candidate is None and not _is_brand_line(line, product_brand):
                    generic_name_candidate = ExtractedField(
                        field_key=DeclarationField.GENERIC_NAME,
                        value=line,
                        confidence=block.confidence,
                        source_evidence_id=evidence.evidence_id,
                        bounding_box=block.bbox,
                        extraction_method="heuristic:generic_name_fallback",
                    )

        if generic_name_candidate is not None:
            maybe_store(generic_name_candidate)

        return list(found.values())
