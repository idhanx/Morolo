# Morolo: 9-Day Hackathon Execution Plan
**Code Coalescence 2025 (CC10) + OpenMetadata Hackathon (T-06: Governance & Classification)**

**Timeline**: April 17–26, 2026 (9 days remaining)  
**Primary Paradox**: T-06 (Governance & Classification)  
**Secondary Paradox**: T-01 (MCP/AI Agents) — via minimal MCP server

---

## Executive Summary

Morolo is a **document-level PII governance extension for OpenMetadata**. It fills the gap between OM's excellent structured data governance and the reality that enterprises have thousands of unstructured documents (PDFs, scanned forms, Word files) full of PII sitting outside any catalog.

**Core Value Proposition**: Upload a PDF with Aadhaar/PAN numbers → Morolo detects PII, calculates risk, creates OM Container entities with classification tags, applies redaction, and creates lineage edges between original and redacted versions — all visible in the OpenMetadata UI.

**Winning Strategy**: Ship a **complete backend** with **basic but functional frontend** + **50-line MCP server** + **pre-baked demo** that shows the OM UI integration (not a reimplementation of it).

---

## Scope Cuts for 9-Day Reality

### ❌ Cut from Original Design
- **ActivityTimeline component** — show audit log as JSON instead
- **LineageGraph (React Flow)** — deep-link to OM UI lineage view instead
- **Framer Motion animations** — use plain CSS transitions
- **Synthetic redaction** — keep Light + Full only (synthetic is demo overkill)
- **Property-based tests** — keep 4 critical ones (Properties 1, 5, 15, 16), skip the rest
- **LocalStorageClient** — MinIO only (Docker Compose handles it)
- **Playwright E2E tests** — manual demo walkthrough instead

### ✅ Keep (Non-Negotiable)
- **All backend services** (Document Processor, PII Detector, Redaction Engine, OM Integration)
- **StorageService registration** (Fix #1 — critical for OM correctness)
- **Presidio built-in recognizers** (Fix #4 — avoids duplicate detection)
- **Circuit breaker for OM** (production-grade resilience)
- **Container entities + lineage + classification tags** (core OM integration)
- **Basic Next.js frontend** (upload + status polling + download + OM deep-links)

### ➕ Add (High-Leverage)
- **MCP server** (50 lines, AI Agent track coverage) — exposes `get_document_risk_score(doc_id)`, `list_pii_entities(doc_id)`, `query_pii_documents(risk_band, limit)` as OM-compatible tools
- **Pre-baked demo assets** (3 sample PDFs with known PII, **pre-processed results stored in DB**) — no live OCR waits during demo
- **OM UI screenshots in README** (show lineage graph, Container catalog, tags, **policy application**)
- **Concrete Policy API integration** (Requirement 8) — DPDP Act policy template JSON + exact API call sequence

---

## 9-Day Task Breakdown

### **Day 1-2: Foundation + Backend Core** (Tasks 1-7)
**Goal**: Working document processing + PII detection pipeline

- [x] 1. Project scaffolding (2 hours)
  - `backend/`, `frontend/`, `docker-compose.yml`, `.env.example`
  - Pin `openmetadata-ingestion>=1.3.0` (StorageService support)
  
- [x] 2. Core types + schemas (2 hours)
  - Enums, Pydantic models, settings

- [x] 3. Database models + Alembic (3 hours)
  - `DocumentJob`, `PIIEntity`, `RedactionReport`, `AuditLog`
  - Initial migration

- [x] 4. MinIO storage client (2 hours)
  - `MinIOStorageClient` only (no local filesystem)

- [x] 5. Metadata parser (1 hour)
  - `json.dumps(model_dump(mode="json"), ...)` — Fix #3

- [x] 6. Document processor (4 hours)
  - pdfminer + Tesseract + python-docx
  - Redis OCR cache

- [x] 7. PII detector with Presidio (4 hours)
  - `AadhaarAliasRecognizer`, `PANAliasRecognizer`, `DrivingLicenseRecognizer` — Fix #4
  - Risk scoring with per-type aggregation

**Checkpoint**: Can extract text from PDF and detect Aadhaar/PAN/DL numbers.

---

### **Day 3-4: Redaction + OM Integration** (Tasks 8-10)
**Goal**: Complete backend pipeline with OM Container creation + lineage

- [x] 8. Checkpoint (30 min)
  - Run unit tests for tasks 5-7

- [x] 9. Redaction engine (3 hours)
  - Light + Full only (skip Synthetic)
  - `IndianIDProvider` for faker (Aadhaar + PAN only)

- [x] 10. **OM Integration Service** (6 hours) — **CRITICAL**
  - `ensure_storage_service()` — Fix #1 (morolo-docs CustomStorage)
  - `ensure_classification_hierarchy()` — IndianGovtID tags
  - `build_container_entity()` — fileFormats, not dataModel; **add dataModel with PII pseudo-schema for better OM UI rendering**
  - `create_lineage_edge()` — parent_container context — Fix #5
  - `register_pipeline_run()` — pipelineType="application" — Fix #2
  - **`create_dpdp_policy_template()` — NEW: Generate DPDP Act masking policy JSON**
  - **`apply_policy(entity_fqn, policy_id)` — NEW: Call OM Policy API with concrete template**
  - Circuit breaker (pybreaker)
  - **Add lineage-specific health check** (separate from general OM connectivity)

**Checkpoint**: Can create Container entities in OM, apply tags, create lineage, **apply policies**.

---

### **Day 5: Celery + FastAPI** (Tasks 11-14)
**Goal**: Complete async processing pipeline + REST API

- [x] 11. Checkpoint (30 min)

- [x] 12. Celery tasks (4 hours)
  - `extract_text_task`, `detect_pii_task`, `redact_document_task`
  - `ingest_to_openmetadata_task`, `ingest_redacted_to_om_task`
  - Retry policy + DLQ

- [x] 13. FastAPI auth + middleware (2 hours)
  - JWT auth, file validation, rate limiting

- [x] 14. FastAPI endpoints (3 hours)
  - `POST /upload`, `POST /redact`, `GET /status/{doc_id}`, `GET /risk-score/{doc_id}`, `GET /audit/{doc_id}`, `GET /health`
  - Startup event: `ensure_storage_service()`

**Checkpoint**: Full backend working end-to-end. Can curl the API.

---

### **Day 6: Minimal Frontend** (Tasks 15-16)
**Goal**: Basic but functional UI — upload + status + download + OM deep-links

- [x] 15. Checkpoint (30 min)

- [x] 16. **Simplified Next.js frontend** (6 hours)
  - **Page 1**: Landing page (hero + "Start" CTA)
  - **Page 2**: Upload page (drag-drop + file validation)
  - **Page 3**: Status page (polling + risk score card + PII list as JSON + download buttons)
  - **Deep-links**: "View in OpenMetadata" button → `{OM_UI_URL}/container/{entity_fqn}`
  - **No React Flow, no ActivityTimeline, no Framer Motion** — just functional shadcn/ui components

**Checkpoint**: Can upload a PDF, see status transitions, download redacted file, click through to OM UI.

---

### **Day 7: MCP Server + Docker** (Tasks 17-18)
**Goal**: T-01 paradox coverage + containerized deployment

- [x] 17. **MCP Server** (2 hours) — **HIGH LEVERAGE - AI AGENT TRACK**
  - Create `mcp-server/` directory
  - Implement three MCP tools as OM-compatible endpoints:
    - `get_document_risk_score(doc_id: str) -> dict` — returns `{doc_id, filename, risk_score, risk_band, pii_breakdown}`
    - `list_pii_entities(doc_id: str) -> list[dict]` — returns PII entity list with types, offsets, confidence
    - `query_pii_documents(risk_band: str, limit: int) -> list[dict]` — queries PostgreSQL `DocumentJob` table filtered by risk band
  - Package as standalone Python script using `mcp` library
  - Add to README: "AI agents can query Morolo's PII catalog via MCP — enables natural language queries like 'show me all HIGH risk documents with Aadhaar numbers'"
  - **This crosses Morolo into the AI Agent track** — judges will see OM + MCP integration

- [x] 18. Docker Compose (3 hours)
  - `backend/Dockerfile`, `frontend/Dockerfile`
  - `docker-compose.yml`: backend, worker, frontend, postgres, redis, minio, openmetadata
  - Health checks, volume mounts, `.env` wiring

**Checkpoint**: `docker-compose up` brings up the full stack.

---

### **Day 8: Demo Prep + Testing** (Tasks 19-20)
**Goal**: Pre-baked demo assets + critical tests passing

- [x] 19. **Demo assets** (3 hours) — **CRITICAL: PRE-BAKED RESULTS**
  - Create 3 sample PDFs:
    1. `aadhaar_sample.pdf` — text PDF with 2 Aadhaar numbers (HIGH risk)
    2. `pan_mixed.pdf` — scanned PDF with 1 PAN + 1 email (MEDIUM risk)
    3. `clean_doc.pdf` — no PII (LOW risk)
  - **Pre-process all 3 through the pipeline and store results in PostgreSQL**
    - Run `extract_text_task`, `detect_pii_task`, `ingest_to_openmetadata_task` for each
    - Store extracted text in Redis cache (keyed by SHA-256)
    - Persist `DocumentJob`, `PIIEntity`, `AuditLog` records
    - Create Container entities in OM with tags and lineage
  - **Demo will show completed state, not live processing** — no OCR waits, no Celery spinners
  - Take screenshots of:
    - OM Container catalog showing all 3 documents with risk scores
    - OM lineage graph showing original → redacted edge
    - OM classification tags on a Container entity (both OM native + Morolo IndianGovtID hierarchy)
    - **Policy application** (if Requirement 8 implemented)
  - Add screenshots to `docs/demo/`
  - Create `docs/demo/DEMO_SCRIPT.md` with exact click-by-click walkthrough

- [x] 20. **Critical tests** (3 hours)
  - Property 1: Indian ID detection (Hypothesis)
  - Property 5: Full redaction completeness (Hypothesis)
  - Property 15: Metadata round-trip (Hypothesis)
  - Unit tests: file validation, risk scoring, OM entity builder
  - Integration test: full upload → detect → redact → OM ingest pipeline

**Checkpoint**: All critical tests pass. Demo assets ready.

---

### **Day 9: README + Demo Video** (Final Polish)
**Goal**: Submission-ready documentation + 3-minute demo video

- [x] **README.md** (2 hours)
  - **Hero section**: "Document PII Governance for OpenMetadata"
  - **Problem**: "OM handles structured data. Enterprises have PDFs full of PII. Morolo bridges the gap."
  - **Architecture diagram**: Mermaid from design.md
  - **Quick start**: `docker-compose up` → open `localhost:3000`
  - **OM Integration showcase**: Embed screenshots of Container catalog, lineage graph, classification tags
  - **MCP Server**: "AI agents can query Morolo via MCP — see `mcp-server/README.md`"
  - **Paradoxes**: "Solves T-06 (Governance) + T-01 (MCP/AI Agents)"
  - **Tech stack**: FastAPI, Celery, Presidio, OpenMetadata SDK, Next.js, Docker

- [x] **Demo video** (2 hours)
  - **0:00-0:30**: Problem statement (show a PDF with visible Aadhaar numbers)
  - **0:30-1:00**: Upload via Morolo UI → status transitions (PENDING → EXTRACTING → PII_DETECTED)
  - **1:00-1:30**: Risk score card + PII entity list + "Apply Redaction" button
  - **1:30-2:00**: Download redacted PDF (show side-by-side: original vs redacted)
  - **2:00-2:30**: Click "View in OpenMetadata" → show Container entity in OM UI → show lineage graph → show classification tags
  - **2:30-3:00**: MCP demo: `mcp query_pii_documents --risk-band=HIGH` → returns JSON list → "AI agents can now govern documents"

- [x] **Submission** (30 min)
  - GitHub repo: `morolo` (public)
  - README, demo video (YouTube unlisted), architecture diagram
  - Tag: `v1.0.0-hackathon`
  - Submit to hackathon portal

---

## Critical Success Factors

### 1. Backend Completeness (Day 1-5)
**Non-negotiable**. The FastAPI + Celery + OM integration is the entire value proposition. If this doesn't work, nothing else matters.

**Validation**: By end of Day 5, you must be able to:
```bash
curl -X POST http://localhost:8000/upload -F "file=@sample.pdf"
# Returns: {"doc_id": "...", "status": "PENDING"}

curl http://localhost:8000/status/{doc_id}
# Returns: {"status": "PII_DETECTED", "risk_score": 78.5, "risk_band": "HIGH", ...}

curl -X POST http://localhost:8000/redact -d '{"doc_id": "...", "redaction_level": "FULL"}'
# Returns: 202 Accepted

# Check OpenMetadata UI: Container entities visible, lineage graph shows original → redacted
```

### 2. MCP Server (Day 7)
**High leverage, low effort**. 50 lines of Python that lets you claim T-01 paradox territory.

**Validation**:
```bash
mcp query_pii_documents --risk-band=HIGH
# Returns: [{"doc_id": "...", "filename": "aadhaar_sample.pdf", "risk_score": 85.2, ...}]
```

### 3. Demo Video Quality (Day 9)
**Judges remember the demo, not the docs**. Pre-bake everything. No live OCR waits. No "oops, let me restart that." Show the OM UI integration — that's your differentiator.

**Script**: Problem (30s) → Upload (30s) → Detection (30s) → Redaction (30s) → OM UI (30s) → MCP (30s) = 3 minutes.

---

## Risk Mitigation

### Risk 1: OpenMetadata SDK version mismatch
**Mitigation**: Pin `openmetadata-ingestion==1.3.3` (latest stable as of April 2026). Test `CreateStorageServiceRequest` import on Day 3 before building OM integration.

### Risk 2: Tesseract OCR too slow for demo
**Mitigation**: Pre-process all demo PDFs. Show pre-cached results. Mention "OCR caching via Redis" in the video.

### Risk 3: Frontend incomplete by Day 6
**Mitigation**: Ship with JSON responses visible in the UI if components aren't styled. Judges care about backend correctness more than UI polish for a governance tool.

### Risk 4: Lineage doesn't render in OM UI
**Mitigation**: Test lineage creation on Day 4. Add **startup health check specifically for lineage API connectivity** (separate from general OM health check). If `parent_container` bug persists, show lineage via OM REST API response in the demo instead of the UI graph.

### Risk 5: Policy API integration is underspecified
**Mitigation**: Create concrete DPDP Act policy template JSON on Day 4 alongside OM integration. Test `apply_policy()` API call with sample Container entity. Document exact API sequence in design.md. This turns Requirement 8 from vague to concrete and scores points on "depth of OM integration."

### Risk 6: Demo shows blank Container entities in OM UI
**Mitigation**: Use `dataModel` to represent PII schema (pseudo-columns per detected PII type with confidence/count metadata). Even though conceptually a stretch for unstructured docs, it makes the OM UI schema tab visually impressive during demo.

---

## Judging Criteria Optimization

| Criterion | Score Target | How to Achieve |
|-----------|--------------|----------------|
| **Potential Impact** | 9/10 | Emphasize DPDP Act compliance gap in README + demo intro |
| **Creativity & Innovation** | 8/10 | MCP server + three-level redaction + OM lineage for documents (novel) + **AI Agent track crossover** |
| **Technical Excellence** | 9/10 | Show: circuit breaker, Redis caching, Presidio built-ins, property tests passing, **concrete policy API integration** |
| **Best Use of OpenMetadata** | 9/10 | Container entities + StorageService + lineage + classification + pipeline runs + **Policy API with DPDP Act template** + **MCP integration** |
| **User Experience** | 7/10 | Basic but functional UI + deep-links to OM UI (honest integration, not reimplementation) + **pre-baked demo (no live waits)** |
| **Presentation Quality** | 9/10 | README with screenshots + 3-min demo video + architecture diagram + **demo script** |

**Estimated Total**: 51/60 (85%) — **Top 3 contender with AI Agent track bonus**

---

## Day-by-Day Checklist

- [ ] **Day 1**: Tasks 1-4 complete, Docker Compose running
- [ ] **Day 2**: Tasks 5-7 complete, can detect PII in uploaded PDF
- [x] **Day 3**: Task 9 complete, can redact documents
- [ ] **Day 4**: Task 10 complete, Container entities visible in OM UI
- [ ] **Day 5**: Tasks 12-14 complete, full API working via curl
- [ ] **Day 6**: Task 16 complete, can upload via UI and see status
- [ ] **Day 7**: Tasks 17-18 complete, MCP server working, Docker Compose stable
- [ ] **Day 8**: Tasks 19-20 complete, demo assets ready, tests passing
- [ ] **Day 9**: README + demo video done, submission uploaded

---

## Final Submission Checklist

- [ ] GitHub repo public with clear README
- [ ] `docker-compose up` works on a fresh clone
- [ ] Demo video uploaded (YouTube unlisted, 3 minutes max)
- [ ] Screenshots of OM UI integration in `docs/demo/`
- [ ] MCP server documented in `mcp-server/README.md`
- [ ] All 6 API endpoints working
- [ ] At least 3 sample documents processed and visible in OM
- [ ] Lineage graph visible in OM UI (or API response shown in demo)
- [ ] Classification tags visible on Container entities
- [ ] Submission form filled with repo link + video link

---

## Bottom Line

**Morolo is a top-3 contender if**:
1. Backend ships complete and correct (Day 1-5)
2. MCP server adds **AI Agent track coverage** (Day 7)
3. Demo video shows OM UI integration, not a reimplementation (Day 9)
4. **Policy API integration is concrete, not aspirational** (Day 4)
5. **Demo uses pre-baked results, not live OCR** (Day 8)

**Cut ruthlessly**. Ship a working backend with a basic frontend. Let the OpenMetadata UI do the heavy lifting for lineage visualization and catalog browsing. That's the whole point of the integration.

**Critical Demo Strategy**: Pre-process all sample documents before recording the demo video. Judges should see:
- Completed Container entities with risk scores and tags
- Lineage graph already rendered in OM UI
- Policy already applied (if implemented)
- MCP server returning results instantly

No spinners. No "let me wait for OCR." No "oops, lineage failed." Show the **end state**, not the processing pipeline.

**You have 9 days. Go win the MacBook.** 🚀
