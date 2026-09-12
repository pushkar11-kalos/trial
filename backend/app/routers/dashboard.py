"""Dashboard statistics."""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.view_models import build_finding_out, build_list_item

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    inspections = (
        db.query(models.Inspection)
        .options(
            joinedload(models.Inspection.product),
            joinedload(models.Inspection.inspector),
            joinedload(models.Inspection.compliance_runs).joinedload(models.ComplianceRun.findings),
        )
        .all()
    )

    total = len(inspections)
    compliant = sum(1 for i in inspections if i.overall_result == models.OverallResult.COMPLIANT)
    non_compliant = sum(1 for i in inspections if i.overall_result == models.OverallResult.NON_COMPLIANT)
    review_required_inspections = sum(
        1 for i in inspections if i.overall_result == models.OverallResult.REVIEW_REQUIRED
    )

    scored = [i.overall_score for i in inspections if i.overall_score is not None]
    avg_score = round(sum(scored) / len(scored), 1) if scored else None

    category_counter: Counter = Counter()
    location_counter: Counter = Counter()
    pending_officer_reviews = 0
    recent_violation_pairs = []

    for insp in inspections:
        if insp.inspection_location:
            location_counter[insp.inspection_location] += 1
        latest = insp.compliance_runs[-1] if insp.compliance_runs else None
        if not latest:
            continue
        for f in latest.findings:
            if f.status == models.FindingStatus.NON_COMPLIANT:
                category_counter[f.category or "Uncategorized"] += 1
                recent_violation_pairs.append((insp.created_at, f))
            if (
                f.status == models.FindingStatus.REVIEW
                and f.counts_toward_score
                and not f.officer_decisions
            ):
                pending_officer_reviews += 1

    recent_violation_pairs.sort(key=lambda pair: pair[0], reverse=True)
    recent_violations = [build_finding_out(f) for _, f in recent_violation_pairs[:5]]

    trend_counter: Counter = Counter()
    for insp in inspections:
        trend_counter[insp.created_at.date().isoformat()] += 1
    trend_points = [schemas.TrendPoint(date=d, count=c) for d, c in sorted(trend_counter.items())]

    recent = sorted(inspections, key=lambda i: i.created_at, reverse=True)[:5]
    active_pack = db.query(models.RulePack).filter(models.RulePack.is_active.is_(True)).first()

    return schemas.DashboardStats(
        total_inspections=total,
        compliant_count=compliant,
        non_compliant_count=non_compliant,
        review_pending_count=review_required_inspections,
        average_compliance_score=avg_score,
        violations_by_category=[
            schemas.CategoryCount(category=c, count=n) for c, n in category_counter.most_common()
        ],
        inspection_trends=trend_points,
        recent_inspections=[build_list_item(i) for i in recent],
        recent_violations=recent_violations,
        pending_officer_reviews=pending_officer_reviews,
        locations_summary=[
            schemas.LocationCount(location=l, count=n) for l, n in location_counter.most_common()
        ],
        active_rule_pack=f"{active_pack.name} ({active_pack.version})" if active_pack else None,
    )
