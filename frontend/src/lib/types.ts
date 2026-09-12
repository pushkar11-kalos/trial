// Mirrors backend/app/schemas.py and models.py enums. Keep values identical
// to the backend's string enum values -- they're compared directly.

export type RoleName = "INSPECTOR" | "SUPERVISOR" | "ADMINISTRATOR";
export type SupplyType = "DOMESTIC" | "IMPORTED";
export type EvidenceType = "FRONT" | "BACK" | "SIDE" | "ADDITIONAL" | "LISTING";
export type InspectionStatus =
  | "DRAFT"
  | "EVIDENCE_UPLOADED"
  | "OCR_COMPLETE"
  | "DECLARATIONS_EXTRACTED"
  | "ANALYZED"
  | "REVIEWED"
  | "FINALIZED";
export type OverallResult = "COMPLIANT" | "NON_COMPLIANT" | "REVIEW_REQUIRED";
export type FindingStatus = "PASS" | "REVIEW" | "NON_COMPLIANT" | "NOT_APPLICABLE";
export type Severity = "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
export type DecisionType = "CONFIRMED" | "DISMISSED" | "MARKED_FOR_REVIEW";
export type ReportType = "PDF" | "DOCX";
export type DemoScenarioKey = "compliant" | "non_compliant" | "review";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: RoleName;
  is_active: boolean;
  is_demo: boolean;
}

export interface Product {
  id: number;
  name: string;
  brand?: string | null;
  category?: string | null;
}

export interface Evidence {
  id: number;
  inspection_id: number;
  image_type: EvidenceType;
  file_path: string;
  original_filename?: string | null;
  content_type?: string | null;
  file_size_bytes?: number | null;
  uploaded_at: string;
  url: string;
}

export interface OCRResult {
  id: number;
  evidence_id: number;
  engine_name?: string | null;
  raw_text?: string | null;
  blocks?: { text: string; bbox: number[]; confidence: number }[] | null;
  overall_confidence?: number | null;
  requires_manual_entry: boolean;
  warnings?: string[] | null;
  processed_at: string;
}

export interface Declaration {
  id: number;
  inspection_id: number;
  field_key: string;
  value: string;
  confidence: number;
  source_evidence_id?: number | null;
  bounding_box?: number[] | null;
  extraction_method: string;
  is_manually_edited: boolean;
  updated_at: string;
}

export interface OfficerDecision {
  id: number;
  finding_id: number;
  officer_id: number;
  officer_name?: string | null;
  decision: DecisionType;
  note?: string | null;
  decided_at: string;
}

export interface Finding {
  id: number;
  rule_id: number;
  rule_code: string;
  rule_name: string;
  category?: string | null;
  status: FindingStatus;
  severity: Severity;
  detected_value?: string | null;
  expected_condition?: string | null;
  explanation?: string | null;
  confidence?: number | null;
  evidence_id?: number | null;
  evidence_bounding_box?: number[] | null;
  counts_toward_score: boolean;
  officer_decisions: OfficerDecision[];
}

export interface ComplianceRun {
  id: number;
  inspection_id: number;
  rule_pack_id: number;
  rule_pack_name?: string | null;
  rule_pack_version?: string | null;
  run_at: string;
  overall_result?: OverallResult | null;
  overall_score?: number | null;
  findings: Finding[];
}

export interface InspectorMini {
  id: number;
  full_name: string;
  email: string;
}

export interface Inspection {
  id: number;
  reference_code: string;
  product: Product;
  inspector: InspectorMini;
  batch_lot?: string | null;
  manufacturer_name?: string | null;
  supply_type: SupplyType;
  inspection_location?: string | null;
  inspection_date?: string | null;
  listing_url?: string | null;
  status: InspectionStatus;
  overall_result?: OverallResult | null;
  overall_score?: number | null;
  demo_scenario?: string | null;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  evidence_items: Evidence[];
  declarations: Declaration[];
  latest_compliance_run?: ComplianceRun | null;
}

export interface InspectionListItem {
  id: number;
  reference_code: string;
  product_name: string;
  brand?: string | null;
  category?: string | null;
  batch_lot?: string | null;
  supply_type: SupplyType;
  inspection_location?: string | null;
  status: InspectionStatus;
  overall_result?: OverallResult | null;
  overall_score?: number | null;
  inspector_name: string;
  inspection_date?: string | null;
  created_at: string;
  demo_scenario?: string | null;
}

export interface Rule {
  id: number;
  rule_code: string;
  name: string;
  description?: string | null;
  category?: string | null;
  severity: Severity;
  applicability?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  required_fields?: string[] | null;
  validation_logic: Record<string, unknown>;
  review_required: boolean;
  counts_toward_score: boolean;
  expected_condition?: string | null;
  source_reference?: string | null;
  is_active: boolean;
}

export interface RulePack {
  id: number;
  name: string;
  version: string;
  description?: string | null;
  is_active: boolean;
  effective_from?: string | null;
  created_at: string;
  rules: Rule[];
}

export interface Report {
  id: number;
  inspection_id: number;
  report_type: ReportType;
  file_path: string;
  generated_at: string;
  url: string;
}

export interface AuditEvent {
  id: number;
  user_id?: number | null;
  user_name?: string | null;
  role_name?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  description?: string | null;
  before?: unknown;
  after?: unknown;
  timestamp: string;
}

export interface CategoryCount {
  category: string;
  count: number;
}
export interface TrendPoint {
  date: string;
  count: number;
}
export interface LocationCount {
  location: string;
  count: number;
}

export interface DashboardStats {
  total_inspections: number;
  compliant_count: number;
  non_compliant_count: number;
  review_pending_count: number;
  average_compliance_score?: number | null;
  violations_by_category: CategoryCount[];
  inspection_trends: TrendPoint[];
  recent_inspections: InspectionListItem[];
  recent_violations: Finding[];
  pending_officer_reviews: number;
  locations_summary: LocationCount[];
  active_rule_pack?: string | null;
}

export interface RepositorySearchResult {
  items: InspectionListItem[];
  total: number;
}

export const DECLARATION_FIELD_LABELS: Record<string, string> = {
  generic_name: "Generic/Common Name",
  manufacturer_name: "Manufacturer/Packer/Importer Name",
  address: "Manufacturer/Packer/Importer Address",
  country_of_origin: "Country of Origin",
  net_quantity: "Net Quantity",
  mrp: "Maximum Retail Price (MRP)",
  mfg_date: "Manufacturing/Packing/Import Date",
  best_before: "Best Before / Use By Date",
  consumer_care: "Consumer/Customer Care Details",
  unit_sale_price: "Unit Sale Price",
  other: "Other Declaration",
};

export const PRODUCT_CATEGORIES = [
  "Food & Beverages",
  "Cosmetics & Personal Care",
  "Household Products",
  "Electronics",
  "Textiles & Apparel",
  "Pharmaceuticals (OTC)",
  "Other",
];
