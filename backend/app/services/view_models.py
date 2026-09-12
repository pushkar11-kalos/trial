"""
ORM -> Pydantic mapping helpers shared by several routers. Kept separate
from schemas.py because these need actual query/relationship logic (e.g.
"the latest compliance run"), not just field mapping.
"""
from typing import Optional

from .. import models, schemas


def build_finding_out(f: models.Finding) -> schemas.FindingOut:
    return schemas.FindingOut(
        id=f.id,
        rule_id=f.rule_id,
        rule_code=f.rule_code,
        rule_name=f.rule_name,
        category=f.category,
        status=f.status,
        severity=f.severity,
        detected_value=f.detected_value,
        expected_condition=f.expected_condition,
        explanation=f.explanation,
        confidence=f.confidence,
        evidence_id=f.evidence_id,
        evidence_bounding_box=f.evidence_bounding_box,
        counts_toward_score=f.counts_toward_score,
        officer_decisions=[
            schemas.OfficerDecisionOut(
                id=d.id,
                finding_id=d.finding_id,
                officer_id=d.officer_id,
                officer_name=_officer_name(d),
                decision=d.decision,
                note=d.note,
                decided_at=d.decided_at,
            )
            for d in f.officer_decisions
        ],
    )


def _officer_name(decision: models.OfficerDecision) -> Optional[str]:
    try:
        return decision.officer.full_name
    except Exception:
        return None


def build_compliance_run_out(run: models.ComplianceRun) -> schemas.ComplianceRunOut:
    return schemas.ComplianceRunOut(
        id=run.id,
        inspection_id=run.inspection_id,
        rule_pack_id=run.rule_pack_id,
        rule_pack_name=run.rule_pack.name if run.rule_pack else None,
        rule_pack_version=run.rule_pack.version if run.rule_pack else None,
        run_at=run.run_at,
        overall_result=run.overall_result,
        overall_score=run.overall_score,
        findings=[build_finding_out(f) for f in run.findings],
    )


def build_inspection_out(insp: models.Inspection) -> schemas.InspectionOut:
    latest_run = insp.compliance_runs[-1] if insp.compliance_runs else None
    return schemas.InspectionOut(
        id=insp.id,
        reference_code=insp.reference_code,
        product=schemas.ProductOut.model_validate(insp.product),
        inspector=schemas.InspectorMini(
            id=insp.inspector.id, full_name=insp.inspector.full_name, email=insp.inspector.email
        ),
        batch_lot=insp.batch_lot,
        manufacturer_name=insp.manufacturer_name,
        supply_type=insp.supply_type,
        inspection_location=insp.inspection_location,
        inspection_date=insp.inspection_date,
        listing_url=insp.listing_url,
        status=insp.status,
        overall_result=insp.overall_result,
        overall_score=insp.overall_score,
        demo_scenario=insp.demo_scenario,
        created_at=insp.created_at,
        updated_at=insp.updated_at,
        finalized_at=insp.finalized_at,
        evidence_items=[schemas.EvidenceOut.model_validate(e) for e in insp.evidence_items],
        declarations=[schemas.DeclarationOut.model_validate(d) for d in insp.declarations],
        latest_compliance_run=build_compliance_run_out(latest_run) if latest_run else None,
    )


def build_list_item(insp: models.Inspection) -> schemas.InspectionListItem:
    return schemas.InspectionListItem(
        id=insp.id,
        reference_code=insp.reference_code,
        product_name=insp.product.name,
        brand=insp.product.brand,
        category=insp.product.category,
        batch_lot=insp.batch_lot,
        supply_type=insp.supply_type,
        inspection_location=insp.inspection_location,
        status=insp.status,
        overall_result=insp.overall_result,
        overall_score=insp.overall_score,
        inspector_name=insp.inspector.full_name,
        inspection_date=insp.inspection_date,
        created_at=insp.created_at,
        demo_scenario=insp.demo_scenario,
    )
