"""
SQLAlchemy ORM models for MetraCheck.

Design notes
------------
- Every enum used in a column is a Python ``str, enum.Enum`` so values are
  readable in the DB and JSON-serializable without extra converters.
- ``Rule.validation_logic`` and other JSON columns use the generic
  ``sqlalchemy.JSON`` type (not Postgres' ``JSONB``) so the same models work
  against SQLite (used for tests / zero-config local dev) and PostgreSQL
  (used by docker-compose) without branching code.
- ``machine_result`` (a Finding, produced by the rule engine) and
  ``officer_decision`` (an OfficerDecision, produced by a human) are always
  stored as separate rows. Confirming or dismissing a finding never mutates
  or deletes the original Finding -- see services/rules/engine.py and
  routers/review.py.
"""
import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RoleName(str, enum.Enum):
    INSPECTOR = "INSPECTOR"
    SUPERVISOR = "SUPERVISOR"
    ADMINISTRATOR = "ADMINISTRATOR"


class SupplyType(str, enum.Enum):
    DOMESTIC = "DOMESTIC"
    IMPORTED = "IMPORTED"


class InspectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    OCR_COMPLETE = "OCR_COMPLETE"
    DECLARATIONS_EXTRACTED = "DECLARATIONS_EXTRACTED"
    ANALYZED = "ANALYZED"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"


class EvidenceType(str, enum.Enum):
    FRONT = "FRONT"
    BACK = "BACK"
    SIDE = "SIDE"
    ADDITIONAL = "ADDITIONAL"
    LISTING = "LISTING"


class DeclarationField(str, enum.Enum):
    GENERIC_NAME = "generic_name"
    MANUFACTURER_NAME = "manufacturer_name"
    ADDRESS = "address"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    NET_QUANTITY = "net_quantity"
    MRP = "mrp"
    MFG_DATE = "mfg_date"
    BEST_BEFORE = "best_before"
    CONSUMER_CARE = "consumer_care"
    UNIT_SALE_PRICE = "unit_sale_price"
    OTHER = "other"


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class FindingStatus(str, enum.Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OverallResult(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DecisionType(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    MARKED_FOR_REVIEW = "MARKED_FOR_REVIEW"


class ReportType(str, enum.Enum):
    PDF = "PDF"
    DOCX = "DOCX"


# ---------------------------------------------------------------------------
# Auth / RBAC
# ---------------------------------------------------------------------------

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    role_name = Column(Enum(RoleName), unique=True, nullable=False, index=True)
    description = Column(String(255), default="")

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    role = relationship("Role", back_populates="users")
    inspections = relationship(
        "Inspection", back_populates="inspector", foreign_keys="Inspection.inspector_id"
    )

    @property
    def role_value(self) -> str:
        return self.role.role_name.value if self.role else ""


# ---------------------------------------------------------------------------
# Product / Inspection
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), index=True)
    category = Column(String(100), index=True)
    default_manufacturer_name = Column(String(255))
    created_at = Column(DateTime, default=utcnow)

    inspections = relationship("Inspection", back_populates="product")


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    reference_code = Column(String(40), unique=True, index=True, nullable=False)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    batch_lot = Column(String(100))
    # Snapshot of the manufacturer/packer/importer name as entered by the
    # officer at Step 2 of the wizard. Deliberately separate from the
    # `manufacturer_name` Declaration extracted from OCR text in Step 4 --
    # the two are expected to usually agree but are never silently merged.
    manufacturer_name = Column(String(255))
    supply_type = Column(Enum(SupplyType), default=SupplyType.DOMESTIC, nullable=False)
    inspection_location = Column(String(255))
    inspection_date = Column(DateTime, default=utcnow)
    listing_url = Column(String(500))

    status = Column(Enum(InspectionStatus), default=InspectionStatus.DRAFT, nullable=False, index=True)
    overall_result = Column(Enum(OverallResult), nullable=True, index=True)
    overall_score = Column(Float, nullable=True)
    rule_pack_id_used = Column(Integer, ForeignKey("rule_packs.id"), nullable=True)

    # "compliant" | "non_compliant" | "review" | None -- set only when created
    # via the Load Hackathon Demo flow, purely informational.
    demo_scenario = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    finalized_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections", foreign_keys=[inspector_id])
    evidence_items = relationship(
        "Evidence", back_populates="inspection", cascade="all, delete-orphan",
        order_by="Evidence.uploaded_at",
    )
    declarations = relationship(
        "Declaration", back_populates="inspection", cascade="all, delete-orphan"
    )
    compliance_runs = relationship(
        "ComplianceRun", back_populates="inspection", cascade="all, delete-orphan",
        order_by="ComplianceRun.run_at",
    )
    reports = relationship("Report", back_populates="inspection", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_inspection_status_result", "status", "overall_result"),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    image_type = Column(Enum(EvidenceType), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    content_type = Column(String(100))
    file_size_bytes = Column(Integer)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=utcnow)

    inspection = relationship("Inspection", back_populates="evidence_items")
    ocr_results = relationship(
        "OCRResult", back_populates="evidence", cascade="all, delete-orphan",
        order_by="OCRResult.processed_at.desc()",
    )


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    engine_name = Column(String(100))
    raw_text = Column(Text)
    blocks = Column(JSON)  # [{text, bbox:[x,y,w,h], confidence}, ...]
    overall_confidence = Column(Float)
    requires_manual_entry = Column(Boolean, default=False)
    warnings = Column(JSON, nullable=True)
    processed_at = Column(DateTime, default=utcnow)

    evidence = relationship("Evidence", back_populates="ocr_results")


class Declaration(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    field_key = Column(Enum(DeclarationField), nullable=False)
    value = Column(Text, default="")
    confidence = Column(Float, default=0)
    source_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    bounding_box = Column(JSON, nullable=True)  # [x, y, w, h] in source image, 0..1 normalized
    extraction_method = Column(String(50), default="regex")  # regex | manual | ai
    is_manually_edited = Column(Boolean, default=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    inspection = relationship("Inspection", back_populates="declarations")

    __table_args__ = (
        Index("ix_declaration_inspection_field", "inspection_id", "field_key"),
    )


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class RulePack(Base):
    __tablename__ = "rule_packs"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=False)
    effective_from = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

    rules = relationship("Rule", back_populates="rule_pack", cascade="all, delete-orphan")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True)
    rule_pack_id = Column(Integer, ForeignKey("rule_packs.id"), nullable=False)
    rule_code = Column(String(50), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    severity = Column(Enum(Severity), nullable=False)
    applicability = Column(Text)  # human readable
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    required_fields = Column(JSON)  # list[str] of DeclarationField values
    validation_logic = Column(JSON, nullable=False)  # {"check": "...", ...params}
    review_required = Column(Boolean, default=False)
    counts_toward_score = Column(Boolean, default=True)
    expected_condition = Column(Text)
    source_reference = Column(Text)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    rule_pack = relationship("RulePack", back_populates="rules")

    __table_args__ = (
        Index("ix_rule_pack_code", "rule_pack_id", "rule_code", unique=True),
    )


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    rule_pack_id = Column(Integer, ForeignKey("rule_packs.id"), nullable=False)
    run_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    run_at = Column(DateTime, default=utcnow)
    overall_result = Column(Enum(OverallResult))
    overall_score = Column(Float, nullable=True)

    inspection = relationship("Inspection", back_populates="compliance_runs")
    rule_pack = relationship("RulePack")
    findings = relationship(
        "Finding", back_populates="compliance_run", cascade="all, delete-orphan",
        order_by="Finding.id",
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    compliance_run_id = Column(Integer, ForeignKey("compliance_runs.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False)

    # Denormalized snapshot of the rule at run time, so historical findings
    # remain accurate/readable even if the rule is edited or deactivated later.
    rule_code = Column(String(50))
    rule_name = Column(String(255))
    category = Column(String(100))

    status = Column(Enum(FindingStatus), index=True, nullable=False)
    severity = Column(Enum(Severity))
    detected_value = Column(Text)
    expected_condition = Column(Text)
    explanation = Column(Text)
    confidence = Column(Float, nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    evidence_bounding_box = Column(JSON, nullable=True)
    counts_toward_score = Column(Boolean, default=True)

    compliance_run = relationship("ComplianceRun", back_populates="findings")
    officer_decisions = relationship(
        "OfficerDecision", back_populates="finding", cascade="all, delete-orphan",
        order_by="OfficerDecision.decided_at",
    )

    @property
    def latest_decision(self):
        return self.officer_decisions[-1] if self.officer_decisions else None


class OfficerDecision(Base):
    """
    A human decision layered on top of a machine Finding. Findings are never
    mutated or deleted when an officer acts -- every decision is a new,
    timestamped row, preserving full history (and feeding the audit trail).
    """
    __tablename__ = "officer_decisions"

    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(Enum(DecisionType), nullable=False)
    note = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=utcnow)

    finding = relationship("Finding", back_populates="officer_decisions")
    officer = relationship("User")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    file_path = Column(String(500), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    generated_at = Column(DateTime, default=utcnow)

    inspection = relationship("Inspection", back_populates="reports")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_name = Column(String(50), nullable=True)
    action = Column(String(100), index=True, nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(50), nullable=True)
    description = Column(Text)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)

    user = relationship("User")
