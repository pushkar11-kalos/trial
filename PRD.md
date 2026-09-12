# MetraCheck — Product Requirements Document

> Captured verbatim (reformatted from the original chat message into clean
> Markdown, no content added or removed) from the project brief supplied at
> the start of this build. The originally-referenced filename
> `MetraCheck_PRD_for_Claude.md` was never actually attached to the
> conversation — this document *is* that PRD, transcribed from the chat
> message text into the repo so it has a durable, versioned home. The
> uploaded `README.md` describing an earlier browser-only prototype is kept
> for reference in the repo root.

## Product

**MetraCheck — AI-Assisted Legal Metrology Compliance & Inspection Platform.**

Not a UI mockup — a fully runnable prototype/MVP: frontend + backend +
database + OCR + rule engine + reports + authentication + demo data.

Make sensible technical decisions without stopping to ask which framework,
database, page layout, APIs, schema, demo products, rule-engine mechanics,
or components to use — this document defines the product. Where an external
API/key is unavailable, build a mock/local implementation so the application
still works.

## Core product

MetraCheck should allow an enforcement officer to:

1. Upload package photographs.
2. Upload multiple views: front/back/side.
3. Extract label text using OCR.
4. Display/edit extracted declarations.
5. Identify mandatory declarations.
6. Run deterministic Legal Metrology compliance checks.
7. Detect missing/suspicious declarations.
8. Perform OCR confidence and readability checks.
9. Flag font-size/readability checks for calibrated vision + officer review
   rather than inventing legal measurements.
10. Show exactly WHY something was flagged.
11. Attach evidence photographs.
12. Let an officer review/confirm findings.
13. Save the inspection.
14. Maintain product and inspection history.
15. Search previous inspections.
16. Generate professional PDF reports.
17. Generate editable DOCX reports.
18. Maintain an audit trail.
19. Provide enforcement dashboards.
20. Provide a configurable/versioned rule engine.

Core architecture: **Image → OCR/CV → Structured Evidence → Rule Engine →
Finding → Officer Review → Final Report.** An LLM/AI must never be the final
legal decision-maker.

## Tech stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui, Recharts,
  responsive desktop/tablet/mobile UI.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- **Database:** PostgreSQL.
- **AI/CV:** an OCR abstraction layer supporting PaddleOCR or Tesseract where
  practical, OpenCV preprocessing, OCR confidence, bounding boxes,
  declaration extraction, and a `MockOCRProvider` so DEMO MODE works without
  any API key.
- **Storage:** local storage in development, structured so S3-compatible
  storage can be added later.
- **Auth:** login, logout, protected routes, RBAC with Inspector, Supervisor,
  and Administrator roles.

## Main application pages

1. **Login** — professional authentication screen with demo accounts
   (`inspector@metracheck.demo`, `supervisor@metracheck.demo`,
   `admin@metracheck.demo`), clearly marked as DEMO accounts.
2. **Dashboard** — total inspections, compliant/non-compliant products,
   reviews pending, average compliance score, violations by category,
   inspection trends, recent inspections, recent violations, pending officer
   reviews, geographic/inspection-location summary, charts where useful, and
   "Start New Inspection" as the primary CTA.
3. **New Inspection** — a guided workflow:
   - **Step 1 — Evidence:** upload front/back/side images plus additional
     evidence, drag-and-drop, thumbnails, removal/reordering.
   - **Step 2 — Product information:** product name, brand, category,
     domestic/imported, batch/lot, manufacturer, inspection location,
     inspection date, inspector, product/listing URL if applicable.
   - **Step 3 — OCR:** a "Run OCR" button; show processing state, extracted
     text, confidence, detected text regions, editable OCR output; allow
     manual correction, clearly labelled as manually edited.
   - **Step 4 — Declaration extraction:** convert OCR text into structured
     fields (generic/common name; manufacturer/packer/importer; address;
     country of origin; net quantity; MRP; MRP tax wording;
     manufacturing/packing/import date; best-before/use-by; consumer care;
     unit sale price; other declarations). For every field show value, OCR
     confidence, source image, bounding box if available, extraction method.

## Rule engine

A real configurable rule engine — rules are structured data, never hardcoded
inside React components. Rule shape:

```text
Rule
 ├── id
 ├── name
 ├── description
 ├── category
 ├── severity
 ├── applicability
 ├── effective_from
 ├── effective_to
 ├── required_fields
 ├── validation_logic
 ├── review_required
 └── source_reference
```

Prototype rules must cover: generic/common name; manufacturer/packer/importer
identity; country of origin for imported goods; net quantity; MRP;
manufacturing/packing/import timing; best-before/use-by where applicable;
consumer-care details; unit sale price where applicable; readability/size
review.

Do not fabricate legal clauses. The system must say: **"Prototype rule pack
— verify against active official legal instruments before operational
enforcement."** The rule pack is versioned, e.g. `PC Rules 2011 + Amendments
— Demo v1`.

## Compliance analysis

An "Analyze Compliance" action shows a professional analysis screen. Each
rule resolves to `✓ PASS`, `⚠ REVIEW`, or `✕ NON-COMPLIANT`. Each finding
shows rule ID, rule name, status, severity, detected value, expected
condition, explanation, confidence, evidence image, evidence region, and
officer actions (Confirm Finding / Mark for Review / Dismiss). Example shape:

```text
NON-COMPLIANT
Country of Origin
Status: Not detected
Applicability: Imported product
Evidence: No country-of-origin declaration detected in the submitted evidence.
Confidence: 94%
Officer action: [Confirm Finding] [Mark for Review] [Dismiss]
```

## Font size / readability (important)

Do not fake millimetre measurements. Distinguish:

- **Automated:** OCR text detection, bounding box detection, pixel-size
  estimation, image quality, contrast/readability indicators.
- **Calibrated measurement:** requires package geometry, calibrated capture,
  a scale/reference, and the applicable legal parameter.

Therefore display: **"Requires calibrated measurement / officer
verification."**

## Officer review

A dedicated review workflow. The officer can confirm a finding, reject it,
mark it for review, add a note, attach evidence, or correct an extracted
declaration. Every change creates an audit event. Flow:

```text
AI Finding → Officer Review → Officer Decision → Final Finding
```

Never silently overwrite AI findings — preserve both `machine_result` and
`officer_decision`.

## Report generation

A professional **PDF Compliance Inspection Report** containing: MetraCheck
logo/name, inspection ID, product, brand, batch, category,
domestic/imported, inspection location, inspector, date, compliance result,
compliance score, rule findings, evidence photographs, extracted
declarations, officer decisions, notes, rule-pack version, audit timestamp,
disclaimer. Also an **editable DOCX** with the same information.

## Product repository

A searchable repository with columns: inspection ID, product, brand, batch,
category, supply type, location, status, score, findings, inspector, date.
Filters: status, category, imported/domestic, date, location, severity.
Clicking a product opens its complete inspection history.

## Audit trail

An immutable-style audit log tracking: login; inspection created; image
uploaded; OCR executed; OCR edited; analysis executed; finding created;
finding confirmed; finding dismissed; report generated; inspection
finalized. Each entry stores user, role, timestamp, action, entity, and
before/after where applicable.

## Admin / rule management

Administrators can view rule packs, rule versions, the active rule pack,
effective dates, rule descriptions, and rule status, and can add/edit demo
rules. Ordinary inspectors cannot change legal rules.

## Demo mode (extremely important)

A prominent **"Load Hackathon Demo"** button instantly loads a realistic
inspection. At least 3 demo cases:

- **Demo 1 — Compliant:** a fictional packaged food product with complete
  declarations. Result: `PASS`.
- **Demo 2 — Non-Compliant:** a fictional imported product with
  intentionally missing/suspicious declarations. Result: `NON-COMPLIANT`.
- **Demo 3 — Review:** a fictional product where OCR confidence/readability/
  calibration creates uncertainty. Result: `REVIEW REQUIRED`.

Never use real companies as examples of legal violations.

## Demo experience

The entire demo should be possible in under 3 minutes:

```text
Login → Dashboard → New Inspection → Load Hackathon Demo → Evidence appears
→ OCR appears → Declarations extracted → Analyze Compliance → Rule-by-rule
findings → Open violation → Review finding → Confirm → Generate Report →
Open PDF/report → Repository → Dashboard updates
```

## UI / UX

Government Enforcement + Modern Enterprise SaaS + AI Operations Center. NOT a
generic startup landing page, flashy neon AI interface, gaming dashboard, or
excessive gradients. Clean white/neutral surfaces, navy/dark sidebar,
professional blue accent, status colors only where meaningful, excellent
typography, dense but readable information, tables, cards, evidence
previews, timelines, badges, tooltips, clear hierarchy. Responsive.

## Database

Proper database models for: User, Role, Inspection, Product, Evidence,
OCRResult, Declaration, RulePack, Rule, ComplianceRun, Finding,
OfficerDecision, Report, AuditEvent — with relationships and indexes,
Alembic migrations, and a seed script.

## API

Documented FastAPI endpoints: Authentication (login, current user);
Inspections (create, list, retrieve, update, finalize); Evidence (upload,
list, delete); OCR (process, retrieve); Declarations (retrieve, update);
Compliance (run, retrieve, findings); Officer review (confirm, dismiss, mark
review); Reports (PDF, DOCX); Repository (search, filters); Rules (list,
retrieve, create/update for admin); Audit (list); Dashboard (statistics).
Include OpenAPI documentation.

## Security

Password hashing; JWT/session authentication; RBAC; protected endpoints;
input validation; upload validation; file size limits; safe filenames; audit
logging; no secrets committed to the repository. Create `.env.example`.
Never require real credentials for DEMO MODE.

## README

An excellent README covering: overview, problem statement, solution,
architecture, features, tech stack, database schema, OCR pipeline, rule
engine, compliance workflow, RBAC, audit trail, report generation, demo
instructions, local setup, Docker setup, environment variables, API
documentation, testing, limitations, future roadmap, legal disclaimer, and
the hackathon demo workflow.

## Docker

`docker-compose.yml` with frontend, backend, and postgres services. The
entire project starts with `docker compose up --build`. Include local
development commands too where practical.

## Testing

Backend: authentication, RBAC, OCR mock, declaration extraction, rule
engine, imported-product conditional rules, findings, officer review, report
generation, audit events. Frontend: navigation, inspection workflow, demo
mode, compliance result rendering.

## Mock data

Realistic but fictional companies/products, e.g. Solara Foods, Aarav
Consumer Products, Glowmint, Northstar Imports. Never claim real companies
are violating the law.

## AI strategy

Replaceable providers:

```text
OCRProvider
 ├── MockOCRProvider
 ├── TesseractOCRProvider
 └── PaddleOCRProvider

DeclarationExtractor
 ├── Regex/RuleExtractor
 └── AIExtractor
```

The deterministic extractor works without external AI. If an LLM provider is
added later it should only help structure/extract information — the final
compliance decision remains with the rule engine + officer.

## Legal design

Never describe the system as "AI determines whether a product is legally
compliant." Describe it as **"AI-assisted compliance screening and evidence
management for Legal Metrology inspections."** Every automated result must
be explainable, every uncertain result reviewable, every final enforcement
decision attributable to an officer. The rule engine must support
amendments/effective dates.

## Hackathon differentiators (prioritize)

1. Explainable compliance: not just `FAIL`, but
   `FAIL → WHY → RULE → EVIDENCE → CONFIDENCE → OFFICER DECISION`.
2. Evidence-aware OCR: show where the declaration came from.
3. Human-in-the-loop enforcement: AI assists, officer decides.
4. Versioned rule engine: rules can change without rewriting the app.
5. Inspection history: an enforcement intelligence repository, not a
   one-time scanner.
6. Calibrated measurement architecture: don't fake font-size compliance;
   build the architecture for real calibrated computer vision.
7. E-commerce support: product-listing text/images as another evidence
   source.

## Final acceptance criteria

Clone/open the repository and run `docker compose up --build`, then:

1. Open the application. 2. Login with demo credentials. 3. See dashboard.
4. Create inspection. 5. Load demo case. 6. See package evidence. 7. Run
OCR. 8. See extracted declarations. 9. Run compliance analysis. 10. See
PASS/FAIL/REVIEW results. 11. Open individual findings. 12. Review/confirm a
finding. 13. Save/finalize inspection. 14. Generate PDF. 15. Generate
editable DOCX. 16. Search the repository. 17. View inspection history. 18.
See dashboard statistics update. 19. View audit trail. 20. View rule
pack/version.

Everything must work without requiring paid APIs.

## Closing instruction (from the brief)

Do not give a tutorial on how to build it — build it. Create the files,
code, database, migrations, UI, APIs, seed data, tests, and documentation.
If something cannot be implemented exactly because an external service is
unavailable, implement a working local/mock equivalent and clearly isolate
it behind an interface. At the end, report: what was built; the project
structure; how to run it; demo credentials; what works fully; what is
mocked; what would be upgraded for production.
