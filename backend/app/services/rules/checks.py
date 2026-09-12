"""
Individual check functions, one per `Rule.validation_logic["check"]` value.
Rules are data (see app/seed_data/rule_pack_v1.json); this module is the
fixed, reviewable set of primitives that data can invoke. Adding a rule that
fits an existing check type is a pure data change (JSON + a DB row) with no
code change required, which is what "rules can change without rewriting the
application" means in practice here.

Every function returns a CheckResult. The confidence-downgrade wrapper (an
otherwise-PASS result gets downgraded to REVIEW when the underlying OCR
confidence is below the configured threshold) lives in engine.py, applied
uniformly after any of these run -- it is not each check function's job.
"""
import datetime as dt
import re
from dataclasses import dataclass
from typing import Dict, Optional

from ...models import FindingStatus, Rule


@dataclass
class DeclarationValue:
    """Decoupled from the SQLAlchemy Declaration model so this module is
    testable without a database."""
    value: str
    confidence: float
    source_evidence_id: Optional[int]
    bounding_box: Optional[list]


@dataclass
class CheckResult:
    status: FindingStatus
    detected_value: str
    explanation: str
    confidence: Optional[float]
    evidence_id: Optional[int]
    evidence_bbox: Optional[list]


DeclarationMap = Dict[str, DeclarationValue]
ProductAttrs = Dict[str, object]

_DATE_PATTERN = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
_MRP_AMOUNT_PATTERN = re.compile(r"(?:Rs\.?|INR)\s?[\d,]+(?:\.\d{1,2})?", re.IGNORECASE)
_TAX_WORDING_PATTERN = re.compile(r"incl", re.IGNORECASE)


def _parse_date(text: str) -> Optional[dt.date]:
    m = _DATE_PATTERN.search(text)
    if not m:
        return None
    d, mo, y = m.groups()
    if len(y) == 2:
        y = "20" + y
    try:
        return dt.date(int(y), int(mo), int(d))
    except ValueError:
        return None


def evaluate_condition(condition: dict, product_attrs: ProductAttrs, declarations: DeclarationMap) -> bool:
    source = condition.get("source")
    if source == "product":
        actual = product_attrs.get(condition["attr"])
        if "equals" in condition:
            return str(actual) == str(condition["equals"])
        if "in" in condition:
            return actual in condition["in"]
        return False
    if source == "declaration":
        decl = declarations.get(condition["field"])
        if decl is None or not decl.value.strip():
            return False
        if "regex" in condition:
            return bool(re.search(condition["regex"], decl.value, re.IGNORECASE))
        return True
    return False


def _not_detected(rule: Rule) -> CheckResult:
    return CheckResult(
        status=FindingStatus.NON_COMPLIANT,
        detected_value="Not detected",
        explanation=(
            f"No '{rule.name}' declaration was detected in the submitted evidence. "
            f"This declaration is required by the applicable rule."
        ),
        confidence=None,
        evidence_id=None,
        evidence_bbox=None,
    )


def _not_applicable(rule: Rule) -> CheckResult:
    return CheckResult(
        status=FindingStatus.NOT_APPLICABLE,
        detected_value="N/A — condition not met",
        explanation=(
            f"This rule applies only when {rule.applicability}. That condition is not "
            f"met for this product/evidence, so the rule is not applicable here."
        ),
        confidence=None,
        evidence_id=None,
        evidence_bbox=None,
    )


def _pass_detected(rule: Rule, decl: DeclarationValue, note: str = "") -> CheckResult:
    return CheckResult(
        status=FindingStatus.PASS,
        detected_value=decl.value,
        explanation=f"'{rule.name}' was detected in the submitted evidence and appears complete.{note}",
        confidence=decl.confidence,
        evidence_id=decl.source_evidence_id,
        evidence_bbox=decl.bounding_box,
    )


def check_field_present(rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs) -> CheckResult:
    field = rule.validation_logic["field"]
    decl = declarations.get(field)
    if decl is None or not decl.value.strip():
        return _not_detected(rule)
    return _pass_detected(rule, decl)


def check_conditional_field_present(
    rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs
) -> CheckResult:
    condition = rule.validation_logic["condition"]
    if not evaluate_condition(condition, product_attrs, declarations):
        return _not_applicable(rule)
    return check_field_present(rule, declarations, product_attrs)


def check_field_present_regex(
    rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs
) -> CheckResult:
    field = rule.validation_logic["field"]
    pattern = rule.validation_logic["pattern"]
    decl = declarations.get(field)
    if decl is None or not decl.value.strip():
        return _not_detected(rule)
    if not re.search(pattern, decl.value, re.IGNORECASE):
        return CheckResult(
            status=FindingStatus.REVIEW,
            detected_value=decl.value,
            explanation=(
                f"'{rule.name}' was detected ('{decl.value}') but does not clearly match "
                f"the expected format for this declaration. Officer verification recommended."
            ),
            confidence=decl.confidence,
            evidence_id=decl.source_evidence_id,
            evidence_bbox=decl.bounding_box,
        )
    return _pass_detected(rule, decl)


def check_field_present_date(
    rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs
) -> CheckResult:
    field = rule.validation_logic["field"]
    decl = declarations.get(field)
    if decl is None or not decl.value.strip():
        return _not_detected(rule)
    if _parse_date(decl.value) is None:
        return CheckResult(
            status=FindingStatus.REVIEW,
            detected_value=decl.value,
            explanation=(
                f"'{rule.name}' text was detected ('{decl.value}') but could not be parsed "
                f"as a valid date. Officer verification recommended."
            ),
            confidence=decl.confidence,
            evidence_id=decl.source_evidence_id,
            evidence_bbox=decl.bounding_box,
        )
    return _pass_detected(rule, decl)


def check_conditional_field_present_date(
    rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs
) -> CheckResult:
    condition = rule.validation_logic["condition"]
    if not evaluate_condition(condition, product_attrs, declarations):
        return _not_applicable(rule)
    return check_field_present_date(rule, declarations, product_attrs)


def check_mrp(rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs) -> CheckResult:
    field = rule.validation_logic.get("field", "mrp")
    decl = declarations.get(field)
    if decl is None or not decl.value.strip():
        return _not_detected(rule)
    if not _MRP_AMOUNT_PATTERN.search(decl.value):
        return CheckResult(
            status=FindingStatus.REVIEW,
            detected_value=decl.value,
            explanation=(
                f"An MRP declaration was detected ('{decl.value}') but no clear numeric "
                f"amount could be confirmed. Officer verification recommended."
            ),
            confidence=decl.confidence,
            evidence_id=decl.source_evidence_id,
            evidence_bbox=decl.bounding_box,
        )
    if not _TAX_WORDING_PATTERN.search(decl.value):
        return CheckResult(
            status=FindingStatus.REVIEW,
            detected_value=decl.value,
            explanation=(
                f"An MRP amount was detected ('{decl.value}') but wording confirming an "
                f"inclusive-of-all-taxes price was not found nearby. Officer verification "
                f"recommended."
            ),
            confidence=decl.confidence,
            evidence_id=decl.source_evidence_id,
            evidence_bbox=decl.bounding_box,
        )
    return _pass_detected(rule, decl)


def check_always_review(rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs) -> CheckResult:
    return CheckResult(
        status=FindingStatus.REVIEW,
        detected_value="Automated signals only (OCR text presence, bounding-box coverage, image "
        "contrast/resolution indicators) — no calibrated legal measurement was performed.",
        explanation=(
            "Font size and label prominence must meet applicable legal minimums, which can only "
            "be confirmed through calibrated measurement (known package geometry, a captured scale "
            "or reference object, and the applicable legal parameter for this declaration/package "
            "size). A photograph alone cannot establish this. An officer must visually and/or "
            "physically verify compliance."
        ),
        confidence=None,
        evidence_id=None,
        evidence_bbox=None,
    )


_DISPATCH = {
    "field_present": check_field_present,
    "conditional_field_present": check_conditional_field_present,
    "field_present_regex": check_field_present_regex,
    "field_present_date": check_field_present_date,
    "conditional_field_present_date": check_conditional_field_present_date,
    "mrp_check": check_mrp,
    "always_review": check_always_review,
}


def run_check(rule: Rule, declarations: DeclarationMap, product_attrs: ProductAttrs) -> CheckResult:
    check_type = rule.validation_logic.get("check")
    fn = _DISPATCH.get(check_type)
    if fn is None:
        raise ValueError(f"Unknown rule check type '{check_type}' on rule {rule.rule_code}")
    return fn(rule, declarations, product_attrs)
