# The Lenny Growth Assistant

A full-stack, grounded AI assistant built on transcripts from Lenny’s Podcast & Newsletter. It features source-cited conversational Q&A, Ship 30 for 30 structured essay generation (~1,250 words), and an interactive Artifact Viewer with sandboxed HTML/CSS and Markdown rendering.

---

## 1. System Architecture Overview

```
                          +---------------------------------------+
                          |   Frontend (React + Artifact Viewer)  |
                          +-------------------+-------------------+
                                              | HTTP / SSE
                                              v
                          +---------------------------------------+
                          |       FastAPI Backend Engine          |
                          |  (/health, /config, /sessions, /chat) |
                          +---------+-------------------+---------+
                                    |                   |
                        Similarity  |                   | Model
                        Retrieval   v                   v Calls
                    +--------------------+    +-----------------------+
                    | PostgreSQL 16      |    | Local Ollama /        |
                    | + pgvector         |    | Anthropic Claude      |
                    +--------------------+    +-----------------------+
```

- **Backend**: FastAPI with async SSE streaming, Pydantic v2 validation, Alembic database migrations, and structured JSON logging.
- **Persistence & Vectors**: PostgreSQL 16 with the `pgvector` extension storing sessions, messages, citations, artifacts, transcripts, and chunk embeddings.
- **AI Models**: Dual-provider architecture supporting **Local Ollama** (mandatory demo: `qwen2.5:7b` / `llama3.1:8b`, embedding: `nomic-embed-text`) and **Cloud Anthropic** (`claude-sonnet-4-5`).
- **Security**: Server-side allowlist HTML sanitization + sandboxed client-side `<iframe>` rendering (`sandbox="allow-same-origin"`, disallowing `allow-scripts`).

---

## 2. Prerequisites

1. **Docker & Docker Compose** (Docker Desktop on Windows/macOS or Docker Engine on Linux).
2. **Ollama** (for local model execution):
   - Download & install from [ollama.com](https://ollama.com).
   - Pull the required models:
     ```bash
     ollama pull nomic-embed-text
     ollama pull qwen2.5:7b
     ```
3. *(Optional)* Anthropic API key if testing cloud provider.

---

## 3. Quickstart (One-Command Startup)

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

Default `.env` values work out-of-the-box for local execution:
```ini
DATABASE_URL=postgresql+psycopg://lenny:postgres123@postgres:5432/lenny_growth
AI_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://host.docker.internal:11434
EMBEDDING_MODEL=nomic-embed-text
ANTHROPIC_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=
```

### 2. Launch the Application Stack
```bash
docker compose up --build
```
This starts:
- **PostgreSQL + pgvector** on `localhost:5432`
- **FastAPI Backend** on `http://localhost:8000` (auto-applies Alembic migrations)
- **Frontend UI & Artifact Viewer** on `http://localhost:5173`

---

## 4. Curated Transcript Ingestion

The repository includes curated transcripts from Lenny's Podcast and Newsletter in `ingestion/transcripts/`.

To ingest, chunk, embed, and index the transcripts into PostgreSQL:

```bash
cd ingestion
python -m venv .venv
# On Linux / macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
DATABASE_URL=postgresql://lenny:postgres123@localhost:5432/lenny_growth python ingest.py
```

Ingestion is idempotent—re-running it will update existing chunks without creating duplicate entries.

---

## 5. Model Configuration & Provider Toggle

The active LLM provider can be switched dynamically without changing application code:

- **Local Ollama** (default):
  ```ini
  AI_PROVIDER=ollama
  OLLAMA_MODEL=qwen2.5:7b
  ```
- **Cloud Anthropic**:
  ```ini
  AI_PROVIDER=anthropic
  ANTHROPIC_API_KEY=sk-ant-api03-...
  ```
- **Automatic Fallback** (optional):
  ```ini
  FALLBACK_PROVIDER=ollama
  ```

The active provider is dynamically surfaced in the UI header and verified via `GET /config`.

---

## 6. Running the Automated Test Suite

Run the full automated test suite (API contracts, retrieval, routing, persistence, sanitizer, essay skill, and resilience failure injections):

### Inside Docker Container
```bash
docker compose exec backend pytest
```

### Locally in Virtual Environment
```bash
cd backend
pytest
```

---

## 7. Manual UI Verification Plan

A complete manual test matrix is documented in [`manual_test_plan.md`](manual_test_plan.md), covering:
- Grounded Q&A with real-time token streaming and citation footers.
- Out-of-corpus abstention test (*"What is the orbital trajectory to Mars?"*).
- Ship 30 for 30 essay generation (~1,250 words, hook, headers, bullets, single takeaway).
- Markdown & HTML/CSS Artifact generation, sandboxed preview, raw toggle, and download.
- Failure-injection tests for all 5 resilience modes.

---

## 8. Resilience & Troubleshooting Matrix

| Issue / Symptom | Root Cause | Solution / Troubleshooting |
|---|---|---|
| `GET /health` returns `503 Service Unavailable` | PostgreSQL container is unreachable or database credentials mismatch. | Run `docker compose logs postgres`. Ensure `DATABASE_URL` matches `POSTGRES_PASSWORD`. |
| *"Local model is unavailable. Start Ollama and try again."* | Ollama is not running on the host machine. | Start Ollama (`ollama serve`) and ensure `nomic-embed-text` and `qwen2.5:7b` are pulled. |
| *"Anthropic is selected but ANTHROPIC_API_KEY is not configured."* | `AI_PROVIDER=anthropic` without valid API key. | Set `ANTHROPIC_API_KEY` in `.env` or switch `AI_PROVIDER=ollama`. |
| Model times out after 60s | Heavy model on CPU or GPU out of memory. | Use a smaller quantized model (e.g. `llama3.2:3b` or `qwen2.5:7b`) or increase `MODEL_TIMEOUT_SECONDS`. |
| Out-of-corpus query returns abstention | Intended behavior: strict cosine distance gating prevents hallucination. | Rephrase query or ask about topics covered in curated transcripts. |

---

## 9. Deliverables Directory Map

- [`PRD.md`](PRD.md) – Product Requirements Document, user personas, success metrics, scope, and flows.
- [`architecture.md`](architecture.md) – System architecture, ER diagrams, API contracts, sandboxing, and deployment topology.
- [`design.md`](design.md) – UI/UX design specifications, accessibility (WCAG 2.1 AA), and interaction states.
- [`manual_test_plan.md`](manual_test_plan.md) – Manual verification matrix and failure injection logs.
- [`agent-transcripts/`](agent-transcripts/) – Logged agent-assisted implementation transcripts with secret scrubbing and error corrections.
