"""
Shared multi-step orchestration used by both the API routers and the seed
script. There is deliberately no separate "seed shortcut" that fabricates a
finished result -- seed.py calls exactly these functions, so a pre-seeded
demo inspection was produced by the same OCR -> extraction -> rule-engine ->
report pipeline a live inspection goes through.

Every function here takes an already-open SQLAlchemy Session and only
flushes (never commits) -- the caller (a router endpoint, or seed.py) owns
the transaction boundary and commits once, atomically, alongside its own
audit event.
"""
import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session

from .. import models
from .audit import record as audit_record
from .extraction.base import EvidenceOCRInput
from .extraction.regex_extractor import RegexDeclarationExtractor
from .ocr.factory import get_ocr_provider
from .reports.context import build_report_context
from .reports.docx_report import generate_docx_report
from .reports.pdf_report import generate_pdf_report
from .rules.engine import RuleEngine
from .storage import StorageBackend


def process_ocr_and_extraction(
    db: Session,
    inspection: models.Inspection,
    storage: StorageBackend,
    user: Optional[models.User],
) -> dict:
    """Runs OCR over every evidence image on the inspection, then runs
    declaration extraction over the combined result. Declarations the
    officer has already manually corrected are left untouched on re-run."""
    ocr_provider = get_ocr_provider()
    extractor = RegexDeclarationExtractor()

    evidence_inputs = []
    ocr_results_created = []

    for evidence in inspection.evidence_items:
        abs_path = storage.absolute_path(evidence.file_path)
        demo_key = (
            f"{inspection.demo_scenario}:{evidence.image_type.value.lower()}"
            if inspection.demo_scenario
            else None
        )

        result = ocr_provider.process(abs_path, demo_key=demo_key)

        ocr_row = models.OCRResult(
            evidence_id=evidence.id,
            engine_name=result.engine_name,
            raw_text=result.raw_text,
            blocks=[{"text": b.text, "bbox": b.bbox, "confidence": b.confidence} for b in result.blocks],
            overall_confidence=result.overall_confidence,
            requires_manual_entry=result.requires_manual_entry,
            warnings=result.warnings,
        )
        db.add(ocr_row)
        ocr_results_created.append(ocr_row)
        evidence_inputs.append(EvidenceOCRInput(evidence_id=evidence.id, blocks=result.blocks))

    audit_record(
        db,
        user,
        "OCR_EXECUTED",
        "Inspection",
        inspection.id,
        description=f"OCR executed across {len(evidence_inputs)} evidence image(s).",
    )

    fields = extractor.extract(evidence_inputs, inspection.product.brand or "")

    existing_by_field = {d.field_key: d for d in inspection.declarations}
    declarations_out = []
    for field in fields:
        current = existing_by_field.get(field.field_key)
        if current is not None and current.is_manually_edited:
            # Never clobber an officer's manual correction on a re-run.
            declarations_out.append(current)
            continue
        if current is not None:
            current.value = field.value
            current.confidence = field.confidence
            current.source_evidence_id = field.source_evidence_id
            current.bounding_box = field.bounding_box
            current.extraction_method = field.extraction_method
            current.is_manually_edited = False
            declarations_out.append(current)
        else:
            new_decl = models.Declaration(
                field_key=field.field_key,
                value=field.value,
                confidence=field.confidence,
                source_evidence_id=field.source_evidence_id,
                bounding_box=field.bounding_box,
                extraction_method=field.extraction_method,
                is_manually_edited=False,
            )
            # Appended to the relationship collection (not just given a raw
            # inspection_id + db.add()) so that `inspection.declarations`,
            # already loaded a few lines above, stays in sync in-memory for
            # any later access in this same session -- e.g. run_compliance()
            # called right after this function, on the same `inspection`
            # object. A raw FK-only insert here previously left that cached
            # collection stale (empty), which silently made every rule
            # think zero declarations existed. Covered by
            # tests/test_compliance_flow.py.
            inspection.declarations.append(new_decl)
            declarations_out.append(new_decl)

    inspection.status = models.InspectionStatus.DECLARATIONS_EXTRACTED
    inspection.updated_at = dt.datetime.utcnow()
    db.flush()

    return {"ocr_results": ocr_results_created, "declarations": declarations_out}


def run_compliance(
    db: Session, inspection: models.Inspection, user: Optional[models.User]
) -> models.ComplianceRun:
    rule_pack = db.query(models.RulePack).filter(models.RulePack.is_active.is_(True)).first()
    if not rule_pack:
        raise ValueError("No active rule pack is configured.")

    rules = [r for r in rule_pack.rules if r.is_active]
    product_attrs = {
        "supply_type": inspection.supply_type.value,
        "category": inspection.product.category,
    }

    engine = RuleEngine()
    drafts, overall, score = engine.run(rules, inspection.declarations, product_attrs)

    run = models.ComplianceRun(
        inspection_id=inspection.id,
        rule_pack_id=rule_pack.id,
        run_by=user.id if user else None,
        overall_result=overall,
        overall_score=score,
    )
    db.add(run)
    db.flush()  # need run.id before attaching findings

    pass_n = review_n = fail_n = 0
    for d in drafts:
        db.add(
            models.Finding(
                compliance_run_id=run.id,
                rule_id=d.rule.id,
                rule_code=d.rule.rule_code,
                rule_name=d.rule.name,
                category=d.rule.category,
                status=d.status,
                severity=d.rule.severity,
                detected_value=d.detected_value,
                expected_condition=d.expected_condition,
                explanation=d.explanation,
                confidence=d.confidence,
                evidence_id=d.evidence_id,
                evidence_bounding_box=d.evidence_bounding_box,
                counts_toward_score=d.counts_toward_score,
            )
        )
        if d.status == models.FindingStatus.PASS:
            pass_n += 1
        elif d.status == models.FindingStatus.REVIEW:
            review_n += 1
        elif d.status == models.FindingStatus.NON_COMPLIANT:
            fail_n += 1

    inspection.status = models.InspectionStatus.ANALYZED
    inspection.overall_result = overall
    inspection.overall_score = score
    inspection.rule_pack_id_used = rule_pack.id
    inspection.updated_at = dt.datetime.utcnow()

    audit_record(
        db,
        user,
        "ANALYSIS_EXECUTED",
        "Inspection",
        inspection.id,
        description=f"Compliance analysis run: {overall.value}, score {score}.",
    )
    audit_record(
        db,
        user,
        "FINDING_CREATED",
        "ComplianceRun",
        run.id,
        description=f"{len(drafts)} finding(s) created ({pass_n} pass, {review_n} review, {fail_n} non-compliant).",
    )

    db.flush()
    return run


_REVIEW_ACTION_BY_DECISION = {
    models.DecisionType.CONFIRMED: "FINDING_CONFIRMED",
    models.DecisionType.DISMISSED: "FINDING_DISMISSED",
    models.DecisionType.MARKED_FOR_REVIEW: "FINDING_MARKED_FOR_REVIEW",
}


def record_officer_decision(
    db: Session,
    finding: models.Finding,
    decision: models.DecisionType,
    note: Optional[str],
    user: models.User,
) -> models.OfficerDecision:
    row = models.OfficerDecision(finding_id=finding.id, officer_id=user.id, decision=decision, note=note)
    db.add(row)

    inspection = finding.compliance_run.inspection
    if inspection.status == models.InspectionStatus.ANALYZED:
        inspection.status = models.InspectionStatus.REVIEWED
        inspection.updated_at = dt.datetime.utcnow()

    audit_record(
        db,
        user,
        _REVIEW_ACTION_BY_DECISION[decision],
        "Finding",
        finding.id,
        description=f"{finding.rule_code} — {decision.value}" + (f': "{note}"' if note else ""),
        before={"status": finding.status.value},
        after={"decision": decision.value, "note": note},
    )
    db.flush()
    return row


def generate_report(
    db: Session,
    inspection: models.Inspection,
    report_type: models.ReportType,
    storage: StorageBackend,
    user: Optional[models.User],
) -> models.Report:
    ctx = build_report_context(inspection, storage)

    if report_type == models.ReportType.PDF:
        data = generate_pdf_report(ctx)
        ext = "pdf"
    else:
        data = generate_docx_report(ctx)
        ext = "docx"

    filename = f"{inspection.reference_code}_report.{ext}"
    rel_path = storage.save(f"reports/{inspection.id}", filename, data)

    report = models.Report(
        inspection_id=inspection.id,
        report_type=report_type,
        file_path=rel_path,
        generated_by=user.id if user else None,
    )
    db.add(report)

    audit_record(
        db,
        user,
        "REPORT_GENERATED",
        "Inspection",
        inspection.id,
        description=f"{report_type.value} report generated.",
    )
    db.flush()
    return report
