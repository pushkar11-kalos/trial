# CLAUDE.md — instructions for whoever (human or agent) works on this repo next

Read this before touching code. It records decisions already made so they
don't get re-litigated or accidentally contradicted in a later session.
`PRD.md` is the source spec; `TODO.md` is the live checklist; `CHANGELOG.md`
is the session-by-session log. This file is "how we build it."

## What this product is, in one breath

An enforcement officer photographs a package, runs OCR, gets structured
declarations, runs a deterministic rule engine against them, and reviews/
confirms the findings before anything is final. Read the full pipeline as:

```
Image → OCR/CV → Structured Evidence → Rule Engine → Finding → Officer Review → Final Report
```

## Non-negotiable product rules

- **The rule engine decides pass/fail, never an LLM.** There is no LLM in
  this codebase at all — OCR is Tesseract/mock, extraction is regex/
  heuristic, and rules are deterministic JSON-configured checks. If an LLM
  extractor is ever added (`AIExtractor` is stubbed as a future slot), it
  may only help structure text; the rule engine + officer still decide.
- **Rules are data, not code.** They live in the `rules` DB table (seeded
  from `app/seed_data/rule_pack_v1.json`), interpreted by a fixed set of
  check functions in `app/services/rules/checks.py`. Never hardcode a legal
  threshold inside a router or a React component.
- **Never fabricate a calibrated measurement.** The readability/font-size
  rule (`RULE-READ-011`) always resolves to `REVIEW`, with an explanation
  that calibrated measurement wasn't performed — never a fake PASS/FAIL on
  font size in mm.
- **`Finding` rows are immutable once created.** An officer's decision is
  always a new `OfficerDecision` row (append-only). Never mutate or delete a
  `Finding` when an officer confirms/dismisses/marks it for review.
- **Every automated claim must say why.** Every `Finding` carries
  `expected_condition` + `explanation` + `confidence` + a link back to the
  evidence image/region it came from.
- **Product framing:** "AI-assisted compliance screening and evidence
  management," never "AI determines legal compliance."
- **Currency/glyphs in generated documents:** always render money as
  `Rs. <amount>` — never the `₹` glyph. ReportLab's base-14 PDF fonts don't
  include U+20B9, so it renders as a black box. Keep this consistent in
  seed data, API responses, and the frontend too, so PDF/DOCX/UI text
  matches exactly.

## Tech stack (decided, don't relitigate)

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic,
  PostgreSQL in Docker / SQLite for zero-config local dev and tests (same
  models work against both — no Postgres-only column types).
- **Auth:** `bcrypt` directly (not passlib — avoids the passlib/bcrypt 4.x
  compatibility break) + `pyjwt`. Token extraction via
  `fastapi.security.HTTPBearer` (not `OAuth2PasswordBearer`), because login
  takes a JSON body (`{email, password}`), not an OAuth2 form — HTTPBearer's
  Swagger "Authorize" dialog accepts a pasted token directly, which matches
  this flow. (Minor consequence: Swagger's Authorize button won't itself
  call `/api/auth/login`; call the endpoint via "Try it out", copy the
  token, paste it into Authorize. Documented in the README.)
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind. shadcn/ui
  components are **hand-rolled from scratch** (button/card/input/tabs/
  dialog/etc. in `src/components/ui/`) following shadcn's own conventions
  (cva for variants, `cn()` helper) rather than pulling in the CLI + Radix,
  to keep the dependency surface small and reliable in a sandboxed build
  environment. `lucide-react` and `recharts` are used as real deps.
- **Reports:** `reportlab` (Platypus/flowables) for PDF, `python-docx` for
  DOCX. Both generated server-side, on demand, from the same inspection
  data shape.
- **OCR:** abstraction in `app/services/ocr/` — `MockOCRProvider` (default,
  zero external deps) and `TesseractOCRProvider` (real, used when
  `OCR_PROVIDER=tesseract` and the `tesseract-ocr` binary is present).
  `MockOCRProvider` itself has three tiers: (1) canned lookup for the 3 demo
  scenarios (deterministic, so the hackathon demo is reproducible), (2) a
  best-effort live `pytesseract` attempt for any other uploaded image if the
  binary happens to be available, (3) an honest "manual entry required"
  result (confidence 0, `requires_manual_entry=True`) if neither applies —
  never a fabricated OCR result.

## Schema decisions beyond the PRD's literal list

The PRD lists `User, Role, Inspection, Product, Evidence, OCRResult,
Declaration, RulePack, Rule, ComplianceRun, Finding, OfficerDecision,
Report, AuditEvent` — all present in `app/models.py`, plus:

- `Role` is a real table (not just an enum column on `User`) seeded with the
  3 fixed roles, matching the PRD's schema list literally.
- `Rule.counts_toward_score: bool` — lets a rule exist and produce a
  `Finding` without affecting the pass/fail score or overall result. Used
  by the readability rule (always `REVIEW`, never blocks a `COMPLIANT`
  result) so Demo 1 can still be a clean PASS while still surfacing the
  "needs calibrated verification" advisory on every inspection.
- `Finding.status` has 4 values, not 3: `PASS | REVIEW | NON_COMPLIANT |
  NOT_APPLICABLE`. `NOT_APPLICABLE` covers e.g. country-of-origin on a
  domestic product — showing it as PASS would be misleading, showing it as
  FAIL would be wrong. Excluded from the score denominator.
- `Rule.validation_logic` conditions can key off **either** the product
  (`{"source": "product", "attr": "supply_type", "equals": "IMPORTED"}`) or
  an already-extracted declaration (`{"source": "declaration", "field":
  "net_quantity", "regex": "\\d+\\s*[xX]\\s*\\d+"}` — used to make the
  unit-sale-price rule apply only when the net-quantity text looks like a
  multipack). See `app/services/rules/checks.py::evaluate_condition`.
- **Confidence-downgrade wrapper:** in `engine.py`, if a rule's own check
  logic would return `PASS` but the underlying declaration's OCR confidence
  is below `settings.OCR_REVIEW_CONFIDENCE_THRESHOLD` (default 75), the
  result is downgraded to `REVIEW` with an appended note. This is what
  makes Demo 3 ("uncertain") actually driven by OCR confidence rather than
  hand-waved.

## Rule pack v1 (11 rules — see `app/seed_data/rule_pack_v1.json`)

`RULE-NAME-001` generic name · `RULE-MFR-002` manufacturer/packer/importer
name · `RULE-ADDR-003` address · `RULE-COO-004` country of origin
(conditional: imported only) · `RULE-NETQTY-005` net quantity ·
`RULE-MRP-006` MRP (compound: amount required, "inclusive of taxes" wording
missing → REVIEW not FAIL) · `RULE-MFGDATE-007` mfg/packing/import date ·
`RULE-BB-008` best-before/use-by (conditional: Food/Cosmetics/Pharma
categories, plus must be a parseable date) · `RULE-CARE-009` consumer care ·
`RULE-USP-010` unit sale price (conditional: net-quantity text looks like a
multipack) · `RULE-READ-011` readability/font size (always REVIEW, advisory,
`counts_toward_score=false`).

## The 3 seeded demo scenarios (must stay internally consistent)

- **`compliant`** — "Solara Multigrain Muesli" (Solara Foods), domestic,
  Food category. All applicable declarations present, OCR confidence
  92-97%. Country-of-origin and unit-sale-price are `NOT_APPLICABLE`
  (domestic, not a multipack). Result: **COMPLIANT**, score 100%.
- **`non_compliant`** — "Northstar Belgian Choco Wafers" (Northstar
  Imports), imported, multipack ("6 x 25 g"). Country of origin is entirely
  absent → NON_COMPLIANT (critical). Consumer care entirely absent →
  NON_COMPLIANT. Unit sale price absent despite the multipack quantity
  triggering applicability → NON_COMPLIANT. MRP present without "inclusive
  of taxes" wording → REVIEW. Everything else present, decent OCR
  confidence (85-91%) — the story here is **missing declarations**, not OCR
  uncertainty. Result: **NON_COMPLIANT**.
- **`review`** — "Glowmint Herbal Face Wash" (Aarav Consumer Products),
  domestic, Cosmetics category. Nothing is actually missing or wrong, but
  address/net-quantity/MRP were captured at low OCR confidence
  (58-72%, below the 75% threshold) and best-before reads "See seal on cap"
  (present, but not a parseable date). Zero NON_COMPLIANT findings — the
  story here is **OCR/readability uncertainty**, contrasting deliberately
  with the `non_compliant` scenario. Result: **REVIEW_REQUIRED**.

If you ever edit the canned OCR text in `app/seed_data/demo_scenarios.py`,
re-check these outcomes still hold (there's a regression test for exactly
this: `tests/test_compliance_flow.py`).

## Frontend design system (planned, not yet built as of this note)

Checked `/mnt/skills/public/frontend-design/SKILL.md` before starting UI
work. The PRD already pins the visual direction (navy sidebar, neutral
white surfaces, professional blue accent, status colors only where
meaningful, no gradients/neon) — per that skill, when the brief pins an
axis, follow it exactly rather than defaulting to the generic AI-design
looks it warns about. Tokens decided so far, to implement when frontend
work resumes:

- **Color:** sidebar `navy-950 #0B1626` / `navy-800 #16263B` (hover/active);
  accent `#1D5FC7`; page background `neutral-50 #F5F7FA`; text
  `neutral-900 #101828` / `neutral-500 #667085`; borders `#E4E7EC`; status
  pass `#1E8E5A`, review `#B7791F`, non-compliant `#C0392B` (institutional,
  not neon-alert).
- **Type:** headings in **IBM Plex Sans** (semi-bold), body in **Source
  Sans 3**, and a **signature detail**: rule codes, inspection reference
  codes, and confidence percentages always render in **IBM Plex Mono**
  inside a small bracketed tag treatment, e.g. `[RULE-COO-004]`. This is
  the one deliberate "signature element" — it's rooted in the product's
  actual pitch (every finding traces to an exact rule ID and evidence
  source), not decoration.
- **Signature layout motif:** the Image → OCR → Rule → Officer chain is
  rendered as a thin-lined horizontal stepper with **square** nodes and
  right-angle connectors (circuit/audit-trace feel), reused on the
  dashboard flow indicator and the finding detail view.
- Minimal, purposeful motion only (state-change transitions) — no
  scroll-triggered reveals; this is a functional enforcement tool.

## Running it

Backend only, no Docker (uses local SQLite by default):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --break-system-packages   # inside this sandbox only; a normal venv doesn't need the flag
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```
Tests: `pytest` from `backend/` (uses an isolated SQLite DB, not your dev DB).

Full stack: `docker compose up --build` from the repo root (compose file
lands in a later session — see `TODO.md`).

## Process notes for whoever resumes this

- Don't ask the project owner scope questions — make the sensible call and
  record it here.
- Work incrementally; update `TODO.md` and `CHANGELOG.md` before stopping,
  every session, even a mid-sized one.
- Before writing backend code, this file + `PRD.md` should be enough
  context; you shouldn't need to re-derive the rule list or demo scenarios
  from scratch.
