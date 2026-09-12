"""
RuleEngine -- orchestrates running every active rule in a rule pack against
an inspection's current declarations, and rolls the individual results up
into an overall result + score.

Deliberately pure/DB-agnostic: it's handed already-loaded Rule rows and
Declaration rows, and returns plain dicts describing findings to create --
it does not write to the database itself (routers/compliance.py does that,
inside one transaction, so a ComplianceRun and all of its Findings are
created atomically).
"""
from dataclasses import dataclass
from typing import List, Optional

from ...config import settings
from ...models import Declaration, FindingStatus, OverallResult, Rule
from .checks import CheckResult, DeclarationValue, run_check


@dataclass
class FindingDraft:
    rule: Rule
    status: FindingStatus
    detected_value: str
    expected_condition: Optional[str]
    explanation: str
    confidence: Optional[float]
    evidence_id: Optional[int]
    evidence_bounding_box: Optional[list]
    counts_toward_score: bool


class RuleEngine:
    def __init__(self, confidence_threshold: Optional[int] = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.OCR_REVIEW_CONFIDENCE_THRESHOLD
        )

    def _apply_confidence_downgrade(self, result: CheckResult) -> CheckResult:
        """A rule's own check logic can only ever pass a field that is
        actually present and well-formed. This step separately guards
        against low OCR confidence: even a well-formed, present declaration
        gets bumped to REVIEW if we weren't confident we read it correctly."""
        if (
            result.status == FindingStatus.PASS
            and result.confidence is not None
            and result.confidence < self.confidence_threshold
        ):
            return CheckResult(
                status=FindingStatus.REVIEW,
                detected_value=result.detected_value,
                explanation=(
                    f"{result.explanation} OCR confidence for this field is "
                    f"{result.confidence:.0f}%, below the {self.confidence_threshold}% "
                    f"verification threshold — please visually confirm against the "
                    f"evidence image before relying on this declaration."
                ),
                confidence=result.confidence,
                evidence_id=result.evidence_id,
                evidence_bbox=result.evidence_bbox,
            )
        return result

    def evaluate_rule(self, rule: Rule, declarations: dict, product_attrs: dict) -> CheckResult:
        result = run_check(rule, declarations, product_attrs)
        return self._apply_confidence_downgrade(result)

    def run(
        self,
        rules: List[Rule],
        declarations_orm: List[Declaration],
        product_attrs: dict,
    ) -> tuple[List[FindingDraft], OverallResult, Optional[float]]:
        declarations = {
            d.field_key.value: DeclarationValue(
                value=d.value or "",
                confidence=d.confidence or 0.0,
                source_evidence_id=d.source_evidence_id,
                bounding_box=d.bounding_box,
            )
            for d in declarations_orm
        }

        drafts: List[FindingDraft] = []
        for rule in sorted((r for r in rules if r.is_active), key=lambda r: r.display_order):
            result = self.evaluate_rule(rule, declarations, product_attrs)
            drafts.append(
                FindingDraft(
                    rule=rule,
                    status=result.status,
                    detected_value=result.detected_value,
                    expected_condition=rule.expected_condition,
                    explanation=result.explanation,
                    confidence=result.confidence,
                    evidence_id=result.evidence_id,
                    evidence_bounding_box=result.evidence_bbox,
                    counts_toward_score=rule.counts_toward_score,
                )
            )

        scoreable = [
            d for d in drafts if d.counts_toward_score and d.status != FindingStatus.NOT_APPLICABLE
        ]
        if any(d.status == FindingStatus.NON_COMPLIANT for d in scoreable):
            overall = OverallResult.NON_COMPLIANT
        elif any(d.status == FindingStatus.REVIEW for d in scoreable):
            overall = OverallResult.REVIEW_REQUIRED
        else:
            overall = OverallResult.COMPLIANT

        score = None
        if scoreable:
            passed = sum(1 for d in scoreable if d.status == FindingStatus.PASS)
            score = round(100 * passed / len(scoreable), 1)

        return drafts, overall, score
