# MetraCheck

**AI-assisted compliance screening and evidence management for Legal Metrology inspections.**

MetraCheck is not an automated legal decision-maker. It turns package
photographs into structured, evidence-linked declarations, runs them through
a deterministic, versioned rule engine, and hands every result — pass,
review, or non-compliant — to a human officer for the final call. Every
automated claim traces back to an exact rule ID and an exact evidence image.

> Prototype rule pack — verify against active official legal instruments
> before operational enforcement. See [Legal disclaimer](#legal-disclaimer).

---

## Table of contents

1. [Overview](#overview) · 2. [Problem statement](#problem-statement) · 3. [Solution](#solution) · 4. [Architecture](#architecture) · 5. [Features](#features) · 6. [Tech stack](#tech-stack) · 7. [Database schema](#database-schema) · 8. [OCR pipeline](#ocr-pipeline) · 9. [Rule engine](#rule-engine) · 10. [Compliance workflow](#compliance-workflow) · 11. [RBAC](#rbac) · 12. [Audit trail](#audit-trail) · 13. [Report generation](#report-generation) · 14. [Demo instructions](#demo-instructions-under-3-minutes) · 15. [Local setup](#local-setup-no-docker) · 16. [Docker setup](#docker-setup) · 17. [Environment variables](#environment-variables) · 18. [API documentation](#api-documentation) · 19. [Testing](#testing) · 20. [Limitations](#limitations) · 21. [Future roadmap](#future-roadmap) · 22. [Legal disclaimer](#legal-disclaimer)

---

## Overview

An enforcement officer photographs a packaged commodity, runs OCR, reviews
the structured declarations that come out of it, runs a rule-engine
compliance analysis, reviews/confirms each finding, and generates a
professional PDF and editable DOCX inspection report — all from one
inspection record that lives on afterward in a searchable repository with a
full audit trail.

```
Image → OCR/CV → Structured Evidence → Rule Engine → Finding → Officer Review → Final Report
```

## Problem statement

Legal Metrology enforcement today is largely manual: an officer reads a
label, mentally checks it against a set of rules they carry in their head or
on paper, and writes up a report from scratch. This doesn't scale, isn't
consistently auditable, and leaves no evidence trail linking a finding back
to the exact photograph and exact rule that produced it.

## Solution

MetraCheck automates the *mechanical* parts of this workflow — text
extraction, structured-field parsing, and rule evaluation — while keeping a
human officer as the only party who can make a finding final. Every
automated result carries its own explanation, its own confidence score, and
a link back to the evidence it came from, so nothing is a black box.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────────┐     ┌─────────────┐     ┌────────────────┐
│   Evidence   │ --> │  OCR / CV     │ --> │ Declaration         │ --> │ Rule Engine  │ --> │ Finding          │
│  (photos)    │     │  provider     │     │ Extractor           │     │ (versioned)  │     │ (PASS/REVIEW/    │
└─────────────┘     └──────────────┘     └────────────────────┘     └─────────────┘     │  NON_COMPLIANT/  │
                                                                                             │  NOT_APPLICABLE) │
                                                                                             └────────┬─────────┘
                                                                                                      v
                                                                          ┌──────────────┐   ┌─────────────────┐
                                                                          │ Officer      │ <-│ Findings shown   │
                                                                          │ Decision     │   │ with full "why"  │
                                                                          │ (append-only)│   └─────────────────┘
                                                                          └──────┬───────┘
                                                                                 v
                                                                     ┌───────────────────────┐
                                                                     │ PDF / DOCX Report +    │
                                                                     │ Repository + Audit Log │
                                                                     └───────────────────────┘
```

- **Frontend:** Next.js (App Router) SPA-style client, talks to the backend
  purely over HTTP/JSON + multipart uploads.
- **Backend:** FastAPI, stateless except for the database and local file
  storage; every provider (OCR, storage) sits behind a small interface so a
  real implementation can replace the mock without touching callers.
- **`machine_result` vs `officer_decision`:** a `Finding` (the rule engine's
  output) is immutable once created. An officer's confirm/dismiss/mark-for-
  review action is always a *new*, timestamped `OfficerDecision` row —
  never a mutation of the Finding. Both are always visible together.

## Features

- Multi-image evidence upload (front/back/side/additional) with drag-and-drop
- OCR abstraction with a zero-dependency mock provider *and* a real
  Tesseract + OpenCV-preprocessing provider
- Deterministic regex/heuristic declaration extraction (no LLM involved)
- An 11-rule, versioned, data-driven rule engine (JSON + DB rows, not
  hardcoded in the UI)
- Confidence-aware findings: low OCR confidence downgrades an otherwise-
  passing field to REVIEW rather than silently passing it
- Explainable findings: rule ID, status, severity, detected value, expected
  condition, plain-language explanation, confidence, and the evidence image/
  region behind every single result
- Full officer review workflow (confirm / dismiss / mark for review + notes)
  with machine/human results kept permanently separate
- Professional PDF and editable DOCX compliance reports, generated on demand
- Searchable, filterable inspection repository
- Immutable-style audit trail across every significant action
- Role-based dashboard, admin rule-pack management
- Three realistic, fictional demo scenarios covering COMPLIANT,
  NON_COMPLIANT, and REVIEW_REQUIRED outcomes, loadable with one click and
  pushed through the *real* pipeline, not a canned screenshot

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, hand-rolled shadcn-style component kit, Recharts, lucide-react |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL (Docker) / SQLite (zero-config local dev & tests) |
| OCR/CV | Tesseract (`pytesseract`) + OpenCV preprocessing, behind a `MockOCRProvider` used by default |
| Reports | ReportLab (PDF), python-docx (DOCX) |
| Auth | `bcrypt` + `PyJWT`, `HTTPBearer` |
| Deployment | Docker Compose (postgres + backend + frontend) |

## Database schema

14 tables: `Role`, `User`, `Product`, `Inspection`, `Evidence`, `OCRResult`,
`Declaration`, `RulePack`, `Rule`, `ComplianceRun`, `Finding`,
`OfficerDecision`, `Report`, `AuditEvent`. Full definitions in
`backend/app/models.py`; the Alembic migration in
`backend/alembic/versions/` is autogenerated directly from these models.
Notable relationships: `Inspection` → many `Evidence` → many `OCRResult`;
`Inspection` → many `Declaration`; `Inspection` → many `ComplianceRun` →
many `Finding` → many `OfficerDecision` (append-only). Indexes exist on all
foreign keys plus `Inspection.status`/`overall_result`,
`Finding.status`, `AuditEvent.action`/`timestamp`, and a unique index on
`(rule_pack_id, rule_code)`.

## OCR pipeline

`backend/app/services/ocr/`:

- **`MockOCRProvider`** (default, `OCR_PROVIDER=mock`) — three tiers: (1) a
  deterministic canned lookup for the 3 seeded demo scenarios, so the
  hackathon walkthrough is exactly reproducible; (2) a best-effort live
  Tesseract attempt for any other image, if the binary is available in the
  environment; (3) an honest "manual entry required" result (confidence 0)
  if neither applies. Never fabricates OCR text.
- **`TesseractOCRProvider`** (`OCR_PROVIDER=tesseract`) — real OCR via
  `pytesseract.image_to_data`, with light OpenCV preprocessing (denoise +
  adaptive threshold) when `opencv-python-headless` is available.
- Both return the same `OCRResult` (raw text, per-line bounding boxes,
  per-line confidence, overall confidence, warnings) so nothing downstream
  cares which one ran.

Declaration extraction (`services/extraction/regex_extractor.py`) is
**fully deterministic** — no AI/LLM anywhere in this codebase. It matches
known label keywords per line (`Mfd by:`, `Net Wt:`, `MRP:`, `Best Before:`,
etc.), falls back to a positional heuristic for the address (the line right
after a manufacturer-name match), and falls back to the first still-unclaimed
line that isn't a substring of the declared brand for the generic/common
name. Every extracted field carries the OCR confidence of the exact line it
came from — there's no separate "extraction confidence."

## Rule engine

Rules are **data**, not code: seeded from
`backend/app/seed_data/rule_pack_v1.json` into the `rules` table, and
evaluated by a small, fixed set of check functions in
`services/rules/checks.py` (`field_present`, `conditional_field_present`,
`field_present_regex`, `field_present_date`,
`conditional_field_present_date`, `mrp_check`, `always_review`). Adding a
rule that fits an existing check type is a pure data change — no code
change, no redeploy.

Current rule pack — **"PC Rules 2011 + Amendments — Demo v1"**, 11 rules:

| Code | Rule | Severity | Notes |
|---|---|---|---|
| RULE-NAME-001 | Generic/Common Name | Major | |
| RULE-MFR-002 | Manufacturer/Packer/Importer Name | Major | |
| RULE-ADDR-003 | Manufacturer/Packer/Importer Address | Major | |
| RULE-COO-004 | Country of Origin | Critical | Applies only if `supply_type == IMPORTED` |
| RULE-NETQTY-005 | Net Quantity | Critical | Regex-validated unit format |
| RULE-MRP-006 | Maximum Retail Price | Critical | Amount + "inclusive of taxes" wording checked separately |
| RULE-MFGDATE-007 | Mfg/Packing/Import Date | Major | Must be a parseable date |
| RULE-BB-008 | Best Before / Use By | Major | Applies only to Food/Cosmetics/Pharma categories |
| RULE-CARE-009 | Consumer/Customer Care | Minor | |
| RULE-USP-010 | Unit Sale Price | Minor | Applies only if net quantity looks like a multipack (`6 x 25 g`) |
| RULE-READ-011 | Readability & Font Size | Info | **Always** REVIEW, advisory, excluded from the score — see below |

**Conditions** can key off either the product (`{"source": "product", "attr":
"supply_type", "equals": "IMPORTED"}`) or an already-extracted declaration's
value (`{"source": "declaration", "field": "net_quantity", "regex":
"\\d+\\s*[xX]\\s*\\d+"}`), which is how the unit-sale-price rule knows to
apply only to multipacks without a separate form field.

**Confidence-downgrade:** independent of each rule's own logic, any
would-be PASS is downgraded to REVIEW if the underlying OCR confidence is
below `OCR_REVIEW_CONFIDENCE_THRESHOLD` (default 75%) — a present,
well-formed declaration we simply weren't confident we read correctly still
gets a human's eyes on it.

**Font size / readability, specifically:** MetraCheck does **not** fabricate
a millimetre measurement from a photograph. `RULE-READ-011` always resolves
to REVIEW with an explanation that calibrated measurement (package
geometry, a captured scale reference, and the applicable legal parameter)
wasn't performed — and it's flagged `counts_toward_score=false`, so it
appears on every inspection as a standing advisory without ever blocking a
genuinely clean COMPLIANT result.

**`NOT_APPLICABLE`** is a real 4th finding status (beyond PASS/REVIEW/
NON_COMPLIANT) — e.g. country-of-origin on a domestic product. It's excluded
from the score denominator so it never misleadingly reads as a pass or fail.

## Compliance workflow

`POST /api/inspections/{id}/compliance/run` loads the active rule pack,
evaluates every active rule against the inspection's current declarations,
and creates one `ComplianceRun` plus one `Finding` per rule, atomically.
Overall result: `NON_COMPLIANT` if any scoreable finding is NON_COMPLIANT,
else `REVIEW_REQUIRED` if any scoreable finding is REVIEW, else
`COMPLIANT`. Score = `100 × pass_count / scoreable_count`.

## RBAC

Three roles — `INSPECTOR`, `SUPERVISOR`, `ADMINISTRATOR` — stored as a real
`Role` table (not just an enum column), joined to `User`. Enforced via a
`require_roles(...)` FastAPI dependency. In this prototype, only
`PATCH /api/rules/{id}` (editing rule metadata) is role-restricted to
Administrator; everything else is available to any authenticated role. This
is a deliberate simplification — see [Limitations](#limitations).

## Audit trail

Every significant action creates an `AuditEvent` in the *same* database
transaction as the action itself (never a background/best-effort write), so
an audit row never exists for a change that didn't actually commit:
`LOGIN`, `INSPECTION_CREATED`, `INSPECTION_UPDATED`, `IMAGE_UPLOADED`,
`EVIDENCE_DELETED`, `OCR_EXECUTED`, `OCR_EDITED`, `ANALYSIS_EXECUTED`,
`FINDING_CREATED`, `FINDING_CONFIRMED`, `FINDING_DISMISSED`,
`FINDING_MARKED_FOR_REVIEW`, `REPORT_GENERATED`, `INSPECTION_FINALIZED`,
`RULE_UPDATED`. `FINDING_CREATED` is logged once per compliance run (with a
pass/review/non-compliant breakdown in the description) rather than once
per individual finding, to keep the log readable.

## Report generation

Both the PDF (`services/reports/pdf_report.py`, ReportLab/Platypus) and the
DOCX (`services/reports/docx_report.py`, python-docx) are built from the
exact same `build_report_context()` dict (`services/reports/context.py`),
so the two formats can never drift out of sync. Both include: MetraCheck
branding, inspection identity, compliance result + score, every finding
with its full explanation and officer decision, the extracted declarations
table, evidence photographs, the rule-pack version, a generation timestamp,
and the disclaimer below. Currency is always rendered as `Rs. <amount>`,
never `₹` — ReportLab's base-14 PDF fonts don't include that glyph and
would render a black box.

## Demo instructions (under 3 minutes)

1. `docker compose up --build`, then open **http://localhost:3000**.
2. Log in with any [demo account](#environment-variables) below (password
   `Demo@1234`) — the login screen has one-click quick-fill buttons.
3. You'll land on the **Dashboard** — already populated with 3 pre-seeded,
   fully-processed inspections (one per outcome) so it isn't empty on first
   load.
4. Click **Start New Inspection**.
5. Click **Load Hackathon Demo** and pick a scenario (Compliant /
   Non-Compliant / Review Required).
6. Click **Run OCR** — watch real (mock-provider) OCR text and confidence
   appear, then the parsed declarations below it.
7. Click **Proceed to Compliance Analysis**, then **Analyze Compliance** —
   watch the rule-by-rule findings appear, each with its own status,
   confidence, and explanation.
8. Open a REVIEW or NON-COMPLIANT finding and click **Confirm** (add an
   optional note).
9. Click **Generate PDF** and **Generate DOCX**, open either.
10. Click **Finalize Inspection**.
11. Go to **Repository**, search for the product — see it listed.
12. Go to **Audit Trail** — see every step you just took, logged.
13. Back on **Dashboard** — the stats have updated.

## Local setup (no Docker)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # defaults to a local SQLite file — no edits needed
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload      # http://localhost:8000, docs at /docs

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env.local         # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                        # http://localhost:3000
```

## Docker setup

```bash
docker compose up --build
```

Starts `postgres` (with a healthcheck the backend waits on),
`backend` (runs `alembic upgrade head` → `python -m app.seed` → `uvicorn`,
via `backend/entrypoint.sh`), and `frontend` (production Next.js build).
Frontend on **http://localhost:3000**, backend/API docs on
**http://localhost:8000/docs**. Postgres data and uploaded evidence/reports
persist in named Docker volumes across restarts.

> **Note on `NEXT_PUBLIC_API_URL`:** this is baked into the frontend's
> client-side JS bundle at *build* time (a Next.js requirement for
> `NEXT_PUBLIC_*` vars) and must be a URL your **browser** can reach —
> `http://localhost:8000`, not the internal compose hostname
> `http://backend:8000`. It's already set correctly as a build arg in
> `docker-compose.yml`; change it there (and rebuild) if you deploy behind a
> different host/port.

## Environment variables

Backend (`backend/.env`, see `backend/.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./metracheck.db` | Postgres URL in Docker |
| `JWT_SECRET_KEY` | dev placeholder | **Change in any real deployment** |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / `720` | |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS |
| `OCR_PROVIDER` | `mock` | or `tesseract` |
| `STORAGE_ROOT` / `DEMO_ASSETS_ROOT` | `./storage/...` | Local filesystem paths |
| `MAX_UPLOAD_MB` | `10` | |
| `OCR_REVIEW_CONFIDENCE_THRESHOLD` | `75` | |

Frontend (`frontend/.env.local`, see `frontend/.env.example`):

| Variable | Default |
|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

**Demo accounts** (password for all three: `Demo@1234`) — clearly marked as
demo accounts in the login UI, no real credentials ever required:

| Role | Email |
|---|---|
| Inspector | `inspector@metracheck.demo` |
| Supervisor | `supervisor@metracheck.demo` |
| Administrator | `admin@metracheck.demo` |

## API documentation

Interactive OpenAPI docs at **`/docs`** once the backend is running (27
endpoints across auth, inspections, evidence, OCR, declarations,
compliance, review, reports, repository, rules, audit, dashboard, and
demo). The `/docs` "Authorize" button expects a bearer token pasted
directly (login uses a JSON body, not an OAuth2 form) — call
`POST /api/auth/login` via "Try it out", copy `access_token`, then paste it
into Authorize.

## Testing

**What was actually run and passed, live, in this build:**
- A standalone script exercising `MockOCRProvider` → `RegexDeclarationExtractor`
  → `RuleEngine` against all 3 demo scenarios with zero DB involved —
  confirmed exact expected outcomes (COMPLIANT/100%, NON_COMPLIANT/60%,
  REVIEW_REQUIRED/50%).
- A full database-backed run: `alembic upgrade head` → `python -m app.seed`
  against a real SQLite database, confirming the identical outcomes through
  the real ORM/pipeline path (this run caught and fixed a real bug — a
  stale in-memory SQLAlchemy relationship cache that only manifested when
  OCR+extraction and compliance-analysis were chained in one long-lived
  session, as the seed script does).
- A full HTTP-level, end-to-end replay of the entire demo journey against a
  live `uvicorn` process — login, dashboard, Load Hackathon Demo, OCR,
  compliance analysis, officer review, PDF **and** DOCX generation (with
  the generated files fetched back and verified as a real PDF and a real
  DOCX, not just "the endpoint returned 200"), finalize, repository search,
  audit trail, and an RBAC check (supervisor correctly blocked with 403,
  admin allowed) — for every one of the 27 API endpoints the frontend uses.
- `npm run build` (a full Next.js production build) and `tsc --noEmit`
  across all 40 frontend files, both clean on the first attempt.

**What is not yet in this repo:** a formal `pytest` suite under
`backend/tests/` and a Docker daemon-verified `docker compose up --build`
(no Docker daemon was available in the sandbox this was built in — the
Dockerfiles and compose file were validated structurally: YAML parses,
build-arg wiring for `NEXT_PUBLIC_API_URL`, healthcheck-gated `depends_on`,
etc., but never actually built into images). Both are the natural next
steps — see [Limitations](#limitations).

## Limitations

- **No formal automated test suite yet.** The verification above is real
  and thorough, but it's a set of one-off scripts, not a `pytest` suite
  that runs in CI. Recommended next step: wrap the existing e2e scripts
  into `pytest` fixtures per PRD's requested coverage (auth, RBAC, OCR
  mock, extraction, rule engine, imported-product conditionals, review,
  reports, repository search).
- **`docker compose up --build` was not run against a real Docker daemon**
  in this environment — please run it yourself as the acceptance check; the
  config was validated structurally, not empirically.
- **Declaration extraction is keyword/regex-based**, tuned against
  realistic but limited label phrasing. Real-world labels vary enormously;
  production use would need a much larger regex/heuristic library or an
  `AIExtractor` (the interface already has a slot for one) used strictly to
  *structure* text, never to decide compliance.
- **RBAC is minimal**: only rule-pack editing is role-gated. A production
  system would likely scope inspection visibility/editing by
  inspector/supervisor hierarchy and restrict the audit trail's visibility.
- **JWT lives in `localStorage`**, not an `httpOnly` cookie — simpler for a
  prototype, more XSS-exposed than a production auth setup should be.
- **UI components are hand-rolled**, not the actual shadcn/ui CLI + Radix
  primitives — same visual/API conventions, smaller dependency surface, but
  without Radix's accessibility hardening (focus trapping, ARIA wiring)
  out of the box.
- **PaddleOCR is not implemented** — only Tesseract and the mock provider.
  The `OCRProvider` interface makes adding it straightforward.
- **No calibrated computer vision** for font-size/readability, by design —
  see the [Rule engine](#rule-engine) section. This is the correct
  behavior, not a gap, but it does mean RULE-READ-011 can never resolve to
  PASS or FAIL on its own.
- **Category list, rule pack content, and legal text are all prototype
  data** — see the [disclaimer](#legal-disclaimer).

## Future roadmap

1. Formal `pytest` suite + CI.
2. Real calibrated measurement architecture: captured reference
   object/scale + package geometry → actual font-size/readability
   determination, still officer-verified.
3. PaddleOCR provider; a genuinely pluggable `AIExtractor` (LLM-assisted
   structuring only, never a compliance decision).
4. S3-compatible storage (the `StorageBackend` interface is already shaped
   for it).
5. Finer-grained RBAC (inspector/supervisor hierarchy, audit visibility
   scoping) and SSO.
6. E-commerce listing ingestion (URL → screenshot/text) as a first-class
   evidence source, per the PRD's "e-commerce support" differentiator.
7. Multi-rule-pack support with a real amendment/versioning UI (schema
   already supports multiple `RulePack` rows and `effective_from/to`
   dates on each `Rule`).

## Legal disclaimer

**Prototype rule pack — verify against active official legal instruments
before operational enforcement.** The rule conditions, applicability
clauses, exemptions, and source references in this repository have **not**
been independently verified against the current, amended official text of
the Legal Metrology (Packaged Commodities) Rules, 2011. No specific rule
numbers or clauses are cited from that instrument — deliberately, to avoid
fabricating legal text. MetraCheck performs **AI-assisted compliance
screening and evidence management**; it does not determine legal
compliance. Every automated result is explainable and reviewable, and every
final enforcement decision is attributable to a human officer, never to the
model. All companies, products, and brands used anywhere in this repository
(Solara Foods, Northstar Imports, Glowmint, Aarav Consumer Products, and
their products) are fictional and used solely to illustrate the
compliance-screening workflow.
#   t r i a l  
 