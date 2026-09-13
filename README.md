# The Lenny Growth Assistant

Phase 1 of a grounded assistant for curated Lenny's Podcast and Newsletter transcripts.

## What is implemented

- Docker Compose services for PostgreSQL with pgvector, FastAPI, and a static frontend placeholder.
- Versioned Alembic migration for sessions, messages, citations, artifacts, transcripts, and chunks.
- `GET /health` with an accurate database probe, `GET /config`, request IDs, and structured JSON logs.
- A local-only Ollama embedding ingestion script that cleans, chunks, traces, and idempotently updates curated Markdown transcripts.

## Start the foundation

1. Copy `.env.example` to `.env` and replace the database password consistently in `POSTGRES_PASSWORD` and `DATABASE_URL`.
2. Run `docker compose up --build`.
3. Open `http://localhost:8000/health`, `http://localhost:8000/config`, and `http://localhost:5173`.

The backend applies migrations before it starts. Once local Ollama has the embedding model (`ollama pull nomic-embed-text`), run ingestion from the host:

```bash
cd ingestion
python -m venv .venv && .venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql://lenny:change-me-before-sharing@localhost:5432/lenny_growth python ingest.py
```

Windows users can use `.venv\\Scripts\\pip install -r requirements.txt` and `$env:DATABASE_URL='...'` before `python ingest.py`.

Run the Phase 1 API checks inside the backend container with `docker compose exec backend pytest`.

## Phase boundaries

Chat, provider execution, retrieval, sessions, content skills, and the Artifact Viewer are intentionally scheduled for Phases 2 and 3. The Phase 1 schema retains their required persistence fields so later work does not need destructive migrations.

## Troubleshooting

- `/health` returns `503`: PostgreSQL is unreachable; check `docker compose logs postgres` and the `DATABASE_URL` password.
- Ingestion reports an embedding failure: start Ollama and pull the configured `EMBEDDING_MODEL`; this pipeline never sends transcript content to a cloud provider.
- The UI says Phase 1: this is expected until the Phase 3 frontend milestone.
