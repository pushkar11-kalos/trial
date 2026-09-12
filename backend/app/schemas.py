"""
Pydantic v2 schemas -- request/response shapes for the FastAPI routers.

Kept in one module (mirroring models.py) since a hackathon-scale backend
doesn't benefit from splitting schemas across a dozen tiny files; every
router imports what it needs from here.
"""
import datetime as dt
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from .models import (
    DecisionType,
    DeclarationField,
    EvidenceType,
    FindingStatus,
    InspectionStatus,
    OverallResult,
    ReportType,
    RoleName,
    Severity,
    SupplyType,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: RoleName
    is_active: bool
    is_demo: bool

    @classmethod
    def from_orm_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.role_name,
            is_active=user.is_active,
            is_demo=user.is_demo,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Product / Inspection
# ---------------------------------------------------------------------------

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None


class InspectionCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    supply_type: SupplyType = SupplyType.DOMESTIC
    batch_lot: Optional[str] = Field(default=None, max_length=100)
    manufacturer_name: Optional[str] = Field(default=None, max_length=255)
    inspection_location: Optional[str] = Field(default=None, max_length=255)
    inspection_date: Optional[dt.datetime] = None
    listing_url: Optional[str] = Field(default=None, max_length=500)


class InspectionUpdate(BaseModel):
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    supply_type: Optional[SupplyType] = None
    batch_lot: Optional[str] = None
    manufacturer_name: Optional[str] = None
    inspection_location: Optional[str] = None
    inspection_date: Optional[dt.datetime] = None
    listing_url: Optional[str] = None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_id: int
    image_type: EvidenceType
    file_path: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    uploaded_at: dt.datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"/media/{self.file_path}"


class OCRBlockOut(BaseModel):
    text: str
    bbox: List[float]  # [x, y, w, h] normalized 0..1
    confidence: float


class OCRResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    evidence_id: int
    engine_name: Optional[str] = None
    raw_text: Optional[str] = None
    blocks: Optional[List[dict]] = None
    overall_confidence: Optional[float] = None
    requires_manual_entry: bool = False
    warnings: Optional[List[str]] = None
    processed_at: dt.datetime


class DeclarationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_id: int
    field_key: DeclarationField
    value: str
    confidence: float
    source_evidence_id: Optional[int] = None
    bounding_box: Optional[List[float]] = None
    extraction_method: str
    is_manually_edited: bool
    updated_at: dt.datetime


class DeclarationUpdate(BaseModel):
    value: str = Field(max_length=2000)


class InspectorMini(BaseModel):
    id: int
    full_name: str
    email: str


class InspectionListItem(BaseModel):
    """Flat shape used by the repository search / dashboard recent lists."""
    id: int
    reference_code: str
    product_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    batch_lot: Optional[str] = None
    supply_type: SupplyType
    inspection_location: Optional[str] = None
    status: InspectionStatus
    overall_result: Optional[OverallResult] = None
    overall_score: Optional[float] = None
    inspector_name: str
    inspection_date: Optional[dt.datetime] = None
    created_at: dt.datetime
    demo_scenario: Optional[str] = None


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: int
    rule_code: str
    rule_name: str
    category: Optional[str] = None
    status: FindingStatus
    severity: Severity
    detected_value: Optional[str] = None
    expected_condition: Optional[str] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    evidence_id: Optional[int] = None
    evidence_bounding_box: Optional[List[float]] = None
    counts_toward_score: bool
    officer_decisions: List["OfficerDecisionOut"] = []


class OfficerDecisionIn(BaseModel):
    decision: DecisionType
    note: Optional[str] = Field(default=None, max_length=2000)


class OfficerDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    finding_id: int
    officer_id: int
    officer_name: Optional[str] = None
    decision: DecisionType
    note: Optional[str] = None
    decided_at: dt.datetime


class ComplianceRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_id: int
    rule_pack_id: int
    rule_pack_name: Optional[str] = None
    rule_pack_version: Optional[str] = None
    run_at: dt.datetime
    overall_result: Optional[OverallResult] = None
    overall_score: Optional[float] = None
    findings: List[FindingOut] = []


class InspectionOut(BaseModel):
    """Full detail shape for the inspection detail/review page."""
    id: int
    reference_code: str
    product: ProductOut
    inspector: InspectorMini
    batch_lot: Optional[str] = None
    manufacturer_name: Optional[str] = None
    supply_type: SupplyType
    inspection_location: Optional[str] = None
    inspection_date: Optional[dt.datetime] = None
    listing_url: Optional[str] = None
    status: InspectionStatus
    overall_result: Optional[OverallResult] = None
    overall_score: Optional[float] = None
    demo_scenario: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime
    finalized_at: Optional[dt.datetime] = None
    evidence_items: List[EvidenceOut] = []
    declarations: List[DeclarationOut] = []
    latest_compliance_run: Optional[ComplianceRunOut] = None


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Severity
    applicability: Optional[str] = None
    effective_from: Optional[dt.datetime] = None
    effective_to: Optional[dt.datetime] = None
    required_fields: Optional[List[str]] = None
    validation_logic: dict
    review_required: bool
    counts_toward_score: bool
    expected_condition: Optional[str] = None
    source_reference: Optional[str] = None
    is_active: bool


class RulePackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    version: str
    description: Optional[str] = None
    is_active: bool
    effective_from: Optional[dt.datetime] = None
    created_at: dt.datetime
    rules: List[RuleOut] = []


class RuleUpdate(BaseModel):
    """Admin-only partial update of a rule's non-structural fields."""
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    is_active: Optional[bool] = None
    effective_to: Optional[dt.datetime] = None


# ---------------------------------------------------------------------------
# Reports / Audit / Dashboard
# ---------------------------------------------------------------------------

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_id: int
    report_type: ReportType
    file_path: str
    generated_at: dt.datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"/media/{self.file_path}"


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    description: Optional[str] = None
    before: Optional[Any] = None
    after: Optional[Any] = None
    timestamp: dt.datetime


class CategoryCount(BaseModel):
    category: str
    count: int


class TrendPoint(BaseModel):
    date: str
    count: int


class LocationCount(BaseModel):
    location: str
    count: int


class DashboardStats(BaseModel):
    total_inspections: int
    compliant_count: int
    non_compliant_count: int
    review_pending_count: int
    average_compliance_score: Optional[float] = None
    violations_by_category: List[CategoryCount] = []
    inspection_trends: List[TrendPoint] = []
    recent_inspections: List[InspectionListItem] = []
    recent_violations: List[FindingOut] = []
    pending_officer_reviews: int = 0
    locations_summary: List[LocationCount] = []
    active_rule_pack: Optional[str] = None


class DemoLoadRequest(BaseModel):
    scenario: Literal["compliant", "non_compliant", "review"]


FindingOut.model_rebuild()
