"""
Idempotent seed script. Run via `python -m app.seed`.

Creates:
  - 3 roles, 3 demo users (one per role)
  - the v1 rule pack (from seed_data/rule_pack_v1.json), marked active
  - 3 fully-processed demo inspections (one per scenario), pushed through
    the EXACT same OCR -> extraction -> compliance -> review -> report
    pipeline a live inspection uses (see services/pipeline.py). Nothing
    here is a hand-written "fake" result -- if the pipeline has a bug,
    seeding fails loudly instead of masking it.

Safe to run multiple times: if any User already exists, the whole seed is
skipped (checked before anything is written).
"""
import datetime as dt
import json
import logging
from pathlib import Path

from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from .security import hash_password
from .seed_data.demo_scenarios import SCENARIOS
from .services import pipeline
from .services.audit import record as audit_record
from .services.demo.assets_generator import generate_all_demo_assets
from .services.storage import get_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metracheck.seed")

DEMO_PASSWORD = "Demo@1234"

_ROLE_SEED = [
    (
        models.RoleName.INSPECTOR,
        "Field inspector: creates inspections, runs OCR/analysis, reviews findings.",
    ),
    (
        models.RoleName.SUPERVISOR,
        "Supervises inspectors; same operational access plus a broader view.",
    ),
    (models.RoleName.ADMINISTRATOR, "Manages users and the rule pack; full access."),
]

_USER_SEED = [
    ("inspector@metracheck.demo", "Asha Verma", models.RoleName.INSPECTOR),
    ("supervisor@metracheck.demo", "Rohan Malhotra", models.RoleName.SUPERVISOR),
    ("admin@metracheck.demo", "Priya Nair", models.RoleName.ADMINISTRATOR),
]

# Which finding(s) get an officer decision during seeding, so the seeded
# inspections don't all look identically "freshly analyzed, untouched".
_SEED_DECISIONS: dict[str, list[tuple[str, models.DecisionType, str]]] = {
    "compliant": [
        (
            "RULE-READ-011",
            models.DecisionType.CONFIRMED,
            "Label print quality checked in hand; legible at normal reading distance.",
        )
    ],
    "non_compliant": [
        (
            "RULE-COO-004",
            models.DecisionType.CONFIRMED,
            "Verified physically: no country-of-origin marking anywhere on the pack.",
        ),
        (
            "RULE-USP-010",
            models.DecisionType.CONFIRMED,
            "Multi-piece pack confirmed (6 units); per-unit price genuinely absent.",
        ),
    ],
    "review": [
        (
            "RULE-ADDR-003",
            models.DecisionType.MARKED_FOR_REVIEW,
            "Requesting a sharper photo of the back panel address block before confirming.",
        )
    ],
}

_SCENARIO_AGE_DAYS = {"compliant": 6, "non_compliant": 3, "review": 1}


def _ensure_roles(db) -> dict[models.RoleName, models.Role]:
    roles = {}
    for role_name, description in _ROLE_SEED:
        role = db.query(models.Role).filter(models.Role.role_name == role_name).first()
        if not role:
            role = models.Role(role_name=role_name, description=description)
            db.add(role)
            db.flush()
        roles[role_name] = role
    return roles


def _ensure_users(db, roles: dict[models.RoleName, models.Role]) -> dict[str, models.User]:
    users = {}
    for email, full_name, role_name in _USER_SEED:
        user = models.User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(DEMO_PASSWORD),
            role_id=roles[role_name].id,
            is_active=True,
            is_demo=True,
        )
        db.add(user)
        db.flush()
        users[role_name.value] = user
    return users


def _ensure_rule_pack(db) -> models.RulePack:
    data_path = Path(__file__).parent / "seed_data" / "rule_pack_v1.json"
    data = json.loads(data_path.read_text())

    pack = models.RulePack(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        is_active=True,
        effective_from=dt.datetime.fromisoformat(data["effective_from"]),
    )
    db.add(pack)
    db.flush()

    for r in data["rules"]:
        db.add(
            models.Rule(
                rule_pack_id=pack.id,
                rule_code=r["rule_code"],
                name=r["name"],
                description=r["description"],
                category=r["category"],
                severity=models.Severity(r["severity"]),
                applicability=r["applicability"],
                effective_from=dt.datetime.fromisoformat(data["effective_from"]),
                required_fields=r["required_fields"],
                validation_logic=r["validation_logic"],
                review_required=r["review_required"],
                counts_toward_score=r["counts_toward_score"],
                expected_condition=r["expected_condition"],
                source_reference=r["source_reference"],
                is_active=True,
                display_order=r["display_order"],
            )
        )
    db.flush()
    return pack


def _seed_demo_inspection(db, scenario_key: str, inspector: models.User, storage) -> models.Inspection:
    scenario = SCENARIOS[scenario_key]

    product = models.Product(name=scenario.product_name, brand=scenario.brand, category=scenario.category)
    db.add(product)
    db.flush()

    inspection = models.Inspection(
        reference_code=f"MC-SEED-{scenario_key.upper()}",
        product_id=product.id,
        inspector_id=inspector.id,
        batch_lot=scenario.batch_lot,
        manufacturer_name=scenario.manufacturer_name,
        supply_type=scenario.supply_type,
        inspection_location=scenario.inspection_location,
        inspection_date=dt.datetime.utcnow() - dt.timedelta(days=_SCENARIO_AGE_DAYS[scenario_key]),
        status=models.InspectionStatus.DRAFT,
        demo_scenario=scenario.key,
    )
    db.add(inspection)
    db.flush()

    for spec in scenario.images:
        asset_path = Path(settings.DEMO_ASSETS_ROOT) / scenario.key / f"{spec.slug}.png"
        data = asset_path.read_bytes()
        rel_path = storage.save(f"inspections/{inspection.id}", f"{spec.slug}.png", data)
        db.add(
            models.Evidence(
                inspection_id=inspection.id,
                image_type=spec.image_type,
                file_path=rel_path,
                original_filename=f"{spec.slug}.png",
                content_type="image/png",
                file_size_bytes=len(data),
                uploaded_by=inspector.id,
            )
        )
    inspection.status = models.InspectionStatus.EVIDENCE_UPLOADED
    audit_record(
        db,
        inspector,
        "INSPECTION_CREATED",
        "Inspection",
        inspection.id,
        description=f"Seed data ({scenario_key}) inspection created.",
    )
    db.flush()

    pipeline.process_ocr_and_extraction(db, inspection, storage, inspector)
    run = pipeline.run_compliance(db, inspection, inspector)

    findings_by_code = {f.rule_code: f for f in run.findings}
    for rule_code, decision, note in _SEED_DECISIONS.get(scenario_key, []):
        finding = findings_by_code.get(rule_code)
        if finding is not None:
            pipeline.record_officer_decision(db, finding, decision, note, inspector)

    inspection.status = models.InspectionStatus.REVIEWED
    db.flush()

    pipeline.generate_report(db, inspection, models.ReportType.PDF, storage, inspector)
    pipeline.generate_report(db, inspection, models.ReportType.DOCX, storage, inspector)

    inspection.status = models.InspectionStatus.FINALIZED
    inspection.finalized_at = dt.datetime.utcnow()
    audit_record(
        db,
        inspector,
        "INSPECTION_FINALIZED",
        "Inspection",
        inspection.id,
        description=f"Seed data ({scenario_key}) inspection finalized.",
    )
    db.flush()

    return inspection


def run_seed() -> None:
    # Safety net only -- in docker-compose, Alembic (`alembic upgrade head`)
    # is the actual source of truth for schema, run before this script.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            logger.info("Users already exist — seed already applied, skipping.")
            return

        logger.info("Seeding roles + demo users...")
        roles = _ensure_roles(db)
        users = _ensure_users(db, roles)
        db.commit()

        logger.info("Seeding rule pack v1...")
        _ensure_rule_pack(db)
        db.commit()

        logger.info("Generating demo label images...")
        generate_all_demo_assets()

        storage = get_storage()
        inspector = users[models.RoleName.INSPECTOR.value]

        for scenario_key in ("compliant", "non_compliant", "review"):
            logger.info("Seeding demo inspection: %s", scenario_key)
            inspection = _seed_demo_inspection(db, scenario_key, inspector, storage)
            db.commit()
            logger.info(
                "  -> %s: overall_result=%s score=%s",
                inspection.reference_code,
                inspection.overall_result.value if inspection.overall_result else None,
                inspection.overall_score,
            )

        logger.info("Seed complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
