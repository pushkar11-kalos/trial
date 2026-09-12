import type {
  AuditEvent,
  ComplianceRun,
  DashboardStats,
  Declaration,
  DemoScenarioKey,
  Evidence,
  Finding,
  Inspection,
  InspectionListItem,
  OCRResult,
  Report,
  RepositorySearchResult,
  Rule,
  RulePack,
  SupplyType,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "metracheck_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const d = data as { detail?: unknown; message?: unknown } | null;
    const message = d?.detail ?? d?.message ?? res.statusText ?? "Request failed";
    throw new ApiError(res.status, typeof message === "string" ? message : JSON.stringify(message));
  }
  return data as T;
}

export function mediaUrl(path: string): string {
  if (!path) return "";
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

// ---- Auth ----
export function login(email: string, password: string) {
  return apiFetch<{ access_token: string; token_type: string; user: User }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}
export function getMe() {
  return apiFetch<User>("/api/auth/me");
}

// ---- Inspections ----
export interface InspectionCreatePayload {
  product_name: string;
  brand?: string;
  category?: string;
  supply_type: SupplyType;
  batch_lot?: string;
  manufacturer_name?: string;
  inspection_location?: string;
  inspection_date?: string;
  listing_url?: string;
}
export function createInspection(payload: InspectionCreatePayload) {
  return apiFetch<Inspection>("/api/inspections", { method: "POST", body: JSON.stringify(payload) });
}
export function listInspections(limit = 50) {
  return apiFetch<InspectionListItem[]>(`/api/inspections?limit=${limit}`);
}
export function getInspection(id: number) {
  return apiFetch<Inspection>(`/api/inspections/${id}`);
}
export function updateInspection(id: number, payload: Partial<InspectionCreatePayload>) {
  return apiFetch<Inspection>(`/api/inspections/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
export function finalizeInspection(id: number) {
  return apiFetch<Inspection>(`/api/inspections/${id}/finalize`, { method: "POST" });
}

// ---- Evidence ----
export function uploadEvidence(inspectionId: number, imageType: string, file: File) {
  const form = new FormData();
  form.append("image_type", imageType);
  form.append("file", file);
  return apiFetch<Evidence>(`/api/inspections/${inspectionId}/evidence`, {
    method: "POST",
    body: form,
  });
}
export function deleteEvidence(evidenceId: number) {
  return apiFetch<void>(`/api/evidence/${evidenceId}`, { method: "DELETE" });
}

// ---- OCR ----
export function runOcr(inspectionId: number) {
  return apiFetch<{ ocr_results: OCRResult[]; declarations: Declaration[] }>(
    `/api/inspections/${inspectionId}/ocr`,
    { method: "POST" }
  );
}

// ---- Declarations ----
export function updateDeclaration(declarationId: number, value: string) {
  return apiFetch<Declaration>(`/api/declarations/${declarationId}`, {
    method: "PATCH",
    body: JSON.stringify({ value }),
  });
}

// ---- Compliance ----
export function runCompliance(inspectionId: number) {
  return apiFetch<ComplianceRun>(`/api/inspections/${inspectionId}/compliance/run`, {
    method: "POST",
  });
}
export function getCompliance(inspectionId: number) {
  return apiFetch<ComplianceRun>(`/api/inspections/${inspectionId}/compliance`);
}

// ---- Review ----
export function reviewFinding(findingId: number, decision: string, note?: string) {
  return apiFetch<Finding>(`/api/findings/${findingId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, note: note || undefined }),
  });
}

// ---- Reports ----
export function generatePdfReport(inspectionId: number) {
  return apiFetch<Report>(`/api/inspections/${inspectionId}/reports/pdf`, { method: "POST" });
}
export function generateDocxReport(inspectionId: number) {
  return apiFetch<Report>(`/api/inspections/${inspectionId}/reports/docx`, { method: "POST" });
}
export function listReports(inspectionId: number) {
  return apiFetch<Report[]>(`/api/inspections/${inspectionId}/reports`);
}

// ---- Repository ----
export interface RepositoryFilters {
  status?: string;
  result?: string;
  category?: string;
  supply_type?: string;
  location?: string;
  severity?: string;
  q?: string;
  skip?: number;
  limit?: number;
}
export function searchRepository(filters: RepositoryFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== null) params.set(k, String(v));
  });
  return apiFetch<RepositorySearchResult>(`/api/repository?${params.toString()}`);
}

// ---- Rules ----
export function listRulePacks() {
  return apiFetch<RulePack[]>("/api/rules/packs");
}
export function getActiveRulePack() {
  return apiFetch<RulePack>("/api/rules/packs/active");
}
export function updateRule(
  ruleId: number,
  payload: Partial<Pick<Rule, "name" | "description" | "severity" | "is_active">>
) {
  return apiFetch<Rule>(`/api/rules/${ruleId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

// ---- Audit ----
export function listAuditEvents(
  params: { entity_type?: string; action?: string; limit?: number } = {}
) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) qs.set(k, String(v));
  });
  return apiFetch<AuditEvent[]>(`/api/audit?${qs.toString()}`);
}

// ---- Dashboard ----
export function getDashboardStats() {
  return apiFetch<DashboardStats>("/api/dashboard/stats");
}

// ---- Demo ----
export function loadDemo(scenario: DemoScenarioKey) {
  return apiFetch<Inspection>("/api/demo/load", {
    method: "POST",
    body: JSON.stringify({ scenario }),
  });
}
