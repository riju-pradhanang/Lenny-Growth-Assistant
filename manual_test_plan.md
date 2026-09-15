# Manual UI & End-to-End Test Plan

**System**: The Lenny Growth Assistant  
**Author**: Riju Pradhanang  
**Status**: Executed & Verified  
**Date**: 2026-09-15  

---

## 1. Overview and Environment Setup

This document records the end-to-end manual verification of **The Lenny Growth Assistant** across all user personas, core functional flows, and failure modes.

### Verification Environment
- **Host**: Windows 11 / WSL2 / Docker Desktop
- **Containers**:
  - `postgres` (PostgreSQL 16 + pgvector) on `localhost:5432`
  - `backend` (FastAPI + Uvicorn) on `http://localhost:8000`
  - `frontend` (Static Web Application) on `http://localhost:5173`
- **Model Providers**:
  - **Local**: Ollama (`qwen2.5:7b` / `llama3.1:8b`, embedding: `nomic-embed-text`) at `http://host.docker.internal:11434`
  - **Cloud**: Anthropic Claude (`claude-sonnet-4-5`) via `ANTHROPIC_API_KEY`

---

## 2. Test Execution Matrix

| # | Test Scenario | Steps Executed | Expected Outcome | Result | Observed Latency / Notes |
|---|---|---|---|---|---|
| **TC-01** | **One-Command Startup & Health Check** | 1. Run `docker compose up --build`<br>2. Check `GET http://localhost:8000/health`<br>3. Check `GET http://localhost:8000/config` | Containers start healthy; `/health` returns `status: "ok"`, `database: "up"`; `/config` returns active provider `ollama`. | **PASS** | Startup in < 15s. HTTP 200 OK. |
| **TC-02** | **Session Creation & Sidebar Listing** | 1. Open `http://localhost:5173`<br>2. Click **+ New Session**<br>3. Verify session appears in sidebar list | A new session ID is generated; label defaults to timestamp/first prompt; sidebar displays last active time. | **PASS** | Session stored in PostgreSQL `sessions` table. |
| **TC-03** | **Grounded Q&A with Inline Citations** | 1. Select session<br>2. Ask: *"What is the core difference between top-down and product-led growth according to Lenny's guests?"*<br>3. Observe streaming response and citations | Response streams token-by-token; citations render with Episode Title, Guest Name, and Source URL link; citations modal opens on click. | **PASS** | Time to first token: ~1.8s. All factual claims grounded in transcript excerpts. |
| **TC-04** | **Multi-Turn Context Resolution** | 1. In same session, ask follow-up: *"How does this apply specifically to B2B SaaS onboarding?"* | Assistant retains prior conversational context and synthesizes B2B onboarding insights without losing thread. | **PASS** | Prior turns included in model context window. |
| **TC-05** | **Out-of-Corpus Query & Abstention** | 1. Ask: *"What is the best way to calculate orbital rocket trajectories for Mars missions?"* | Assistant explicitly declines to answer: *"I don’t have enough supporting material in the available transcript corpus to answer that reliably."* | **PASS** | Zero hallucination. Retrieval threshold properly filtered empty chunk results. |
| **TC-06** | **Ship 30 for 30 Essay Generation** | 1. Prompt: *"Write a Ship 30 for 30 essay on product market fit and retention"*<br>2. Check length and formatting | Intent classified as `essay`; generates ~1,200-word structured piece with strong hook, punchy paragraphs, section headings, bullets, bold emphasis, and single explicit takeaway; structural validator passes. | **PASS** | 1,180 words; structural validator emitted 100% compliance badge. |
| **TC-07** | **Artifact Generation (HTML/CSS Widget)** | 1. Click **Generate HTML** or ask: *"Generate an HTML card artifact for the user activation checklist"*<br>2. Check right Artifact Viewer panel | Artifact panel slides open; renders modern HTML/CSS card preview inside a sandboxed `<iframe>`; script tags stripped; raw code tab available. | **PASS** | Sandboxed with `sandbox="allow-same-origin"` (no `allow-scripts`). Sanitizer stripped all unsafe tags. |
| **TC-08** | **Artifact Generation (Markdown Document)** | 1. Click **Generate Markdown** or prompt: *"Turn this into a Markdown artifact"*<br>2. Inspect rendered Markdown and Raw tabs | Markdown renders cleanly with headers, tables, and checklist formatting; raw code toggle displays verbatim markdown; download button exports `.md` file. | **PASS** | Download button downloads `artifact-<id>.md` successfully. |
| **TC-09** | **Provider Toggle & Fallback Banner** | 1. Change `AI_PROVIDER=anthropic` in `.env` (or configure fallback)<br>2. Reload UI<br>3. Verify badge in header | Header badge immediately updates to `anthropic (claude-sonnet-4-5)`; responses stream via Anthropic API; fallback indicator works if configured. | **PASS** | Dynamic provider configuration without frontend recompilation. |
| **TC-10** | **Session Cascade Deletion** | 1. Click Delete button on session in sidebar<br>2. Verify removal from sidebar and database | Session and all associated messages, citations, and artifacts are cleanly cascade-deleted from PostgreSQL. | **PASS** | Foreign key constraints cascade correctly. |

---

## 3. Failure Mode & Resilience Test Matrix

| # | Failure Scenario | Trigger Method | Expected Behavior | Result | Notes |
|---|---|---|---|---|---|
| **FT-01** | **Missing Cloud API Key** | Set `AI_PROVIDER=anthropic` with `ANTHROPIC_API_KEY=""` | UI shows actionable error banner: *"Anthropic is selected but ANTHROPIC_API_KEY is not configured."* Suggests switching to Ollama. | **PASS** | Handled by `ProviderUnavailable` exception without server crash. |
| **FT-02** | **Unreachable Ollama Instance** | Stop Ollama daemon or set `OLLAMA_BASE_URL="http://invalid-host:11434"` | SSE stream emits structured error: `code: "provider_unavailable"`, message: *"Local model is unavailable. Start Ollama and try again."* | **PASS** | No unhandled 500 error; UI renders human-readable recovery prompt. |
| **FT-03** | **Model Request Timeout** | Set `MODEL_TIMEOUT_SECONDS=0.001` to trigger immediate timeout | Error surfaced: *"Model request timed out after 0.001s. Try again or check model responsiveness."* | **PASS** | Request terminated cleanly; connection pool released. |
| **FT-04** | **Empty Vector Retrieval** | Ask obscure/unrelated topic with high distance threshold | Model abstains politely without generating hallucinated claims. | **PASS** | Abstention message saved and rendered cleanly. |
| **FT-05** | **Database Outage / Unreachable DB** | Stop postgres container (`docker compose stop postgres`) | `GET /health` returns HTTP 503 with `database: "down"`; Chat endpoint emits SSE error `database_unavailable` with human-readable alert. | **PASS** | Backend survives DB downtime gracefully. |

---

## 4. UI/UX & Accessibility Checklist

- [x] **Dark / Light Theme & Contrast**: Color palette meets WCAG 2.1 AA contrast ratio (≥ 4.5:1 for standard text).
- [x] **Keyboard Navigation**: Full keyboard tab accessibility across session sidebar, message input, chat buttons, and artifact modal tabs.
- [x] **Responsive Layout**: Resilient flexbox/grid layout supporting desktop (side-by-side chat and artifact viewer) and mobile/tablet (collapsible sidebar, responsive tabs).
- [x] **Streaming State Feedback**: Real-time pulsing indicator and typing animation while assistant generates tokens.
- [x] **Sandboxed Security Notice**: Clear security badge in the Artifact Viewer informing the evaluator that HTML scripts and unsafe tags are blocked.

---

## 5. Conclusion

All 10 user journey scenarios and all 5 failure-injection tests executed with **100% Pass Rate**. The system is hardened, resilient, and ready for evaluator handoff and production demo.
