"""
Builds a single, plain-dict "report context" from an Inspection ORM graph.
Both pdf_report.py and docx_report.py consume exactly this shape, so the
two output formats can never drift out of sync with each other.
"""
import datetime as dt
from typing import Any, Optional

from ... import models
from ..storage import StorageBackend

FIELD_LABELS = {
    "generic_name": "Generic/Common Name",
    "manufacturer_name": "Manufacturer/Packer/Importer Name",
    "address": "Manufacturer/Packer/Importer Address",
    "country_of_origin": "Country of Origin",
    "net_quantity": "Net Quantity",
    "mrp": "Maximum Retail Price (MRP)",
    "mfg_date": "Manufacturing/Packing/Import Date",
    "best_before": "Best Before / Use By Date",
    "consumer_care": "Consumer/Customer Care Details",
    "unit_sale_price": "Unit Sale Price",
    "other": "Other Declaration",
}

DISCLAIMER = (
    "This report presents AI-assisted compliance screening and evidence management output "
    "for Legal Metrology inspections. It does not constitute an automated legal determination "
    "of compliance. Automated findings are produced by a deterministic, versioned rule engine "
    "from OCR-extracted evidence and must be read together with the officer decisions recorded "
    "in this report. This is a prototype rule pack — verify every rule condition, exemption, "
    "date, and measurement method against the currently active official legal instruments "
    "before any operational enforcement action."
)


def _evidence_type_label(evidence: Optional[models.Evidence]) -> Optional[str]:
    if not evidence:
        return None
    return evidence.image_type.value.title()


def build_report_context(
    inspection: models.Inspection, storage: StorageBackend
) -> dict[str, Any]:
    latest_run = inspection.compliance_runs[-1] if inspection.compliance_runs else None

    evidence_by_id = {e.id: e for e in inspection.evidence_items}

    findings_ctx = []
    if latest_run:
        for f in latest_run.findings:
            latest_decision = f.officer_decisions[-1] if f.officer_decisions else None
            findings_ctx.append(
                {
                    "rule_code": f.rule_code,
                    "rule_name": f.rule_name,
                    "category": f.category,
                    "status": f.status.value,
                    "severity": f.severity.value if f.severity else None,
                    "detected_value": f.detected_value,
                    "expected_condition": f.expected_condition,
                    "explanation": f.explanation,
                    "confidence": f.confidence,
                    "evidence_image_type": _evidence_type_label(evidence_by_id.get(f.evidence_id)),
                    "officer_decision": (
                        {
                            "decision": latest_decision.decision.value,
                            "officer_name": (
                                latest_decision.officer.full_name
                                if latest_decision.officer
                                else "Unknown"
                            ),
                            "note": latest_decision.note,
                            "decided_at": latest_decision.decided_at,
                        }
                        if latest_decision
                        else None
                    ),
                }
            )

    declarations_ctx = []
    for d in inspection.declarations:
        declarations_ctx.append(
            {
                "field_key": d.field_key.value,
                "field_label": FIELD_LABELS.get(d.field_key.value, d.field_key.value),
                "value": d.value,
                "confidence": d.confidence,
                "source_image_type": _evidence_type_label(evidence_by_id.get(d.source_evidence_id)),
                "extraction_method": d.extraction_method,
                "is_manually_edited": d.is_manually_edited,
            }
        )

    evidence_ctx = []
    for e in inspection.evidence_items:
        try:
            abs_path = storage.absolute_path(e.file_path)
        except Exception:
            abs_path = None
        evidence_ctx.append(
            {
                "image_type": e.image_type.value.title(),
                "absolute_path": abs_path,
                "original_filename": e.original_filename,
            }
        )

    return {
        "reference_code": inspection.reference_code,
        "product_name": inspection.product.name,
        "brand": inspection.product.brand,
        "batch_lot": inspection.batch_lot,
        "category": inspection.product.category,
        "supply_type": inspection.supply_type.value,
        "manufacturer_name": inspection.manufacturer_name,
        "inspection_location": inspection.inspection_location,
        "inspector_name": inspection.inspector.full_name,
        "inspection_date": inspection.inspection_date,
        "overall_result": inspection.overall_result.value if inspection.overall_result else "Not yet analyzed",
        "overall_score": inspection.overall_score,
        "rule_pack_name": latest_run.rule_pack.name if latest_run and latest_run.rule_pack else None,
        "rule_pack_version": latest_run.rule_pack.version if latest_run and latest_run.rule_pack else None,
        "generated_at": dt.datetime.utcnow(),
        "declarations": declarations_ctx,
        "findings": findings_ctx,
        "evidence_images": evidence_ctx,
        "disclaimer": DISCLAIMER,
    }
