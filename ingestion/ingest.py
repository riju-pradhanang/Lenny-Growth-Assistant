"""Idempotently ingest curated Markdown transcripts using local Ollama embeddings."""
import hashlib
import json
import os
import re
from pathlib import Path

import httpx
import psycopg

ROOT = Path(__file__).parent
TRANSCRIPTS = ROOT / "transcripts"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://lenny:postgres123@localhost:5432/lenny_growth").replace("+psycopg", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))


def parse_source(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    _, header, body = raw.split("---", 2)
    metadata = dict(line.split(":", 1) for line in header.strip().splitlines() if ":" in line)
    return {key.strip(): value.strip() for key, value in metadata.items()}, clean(body)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", "", text)).strip()


def chunks(text: str) -> list[str]:
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    return [text[index:index + CHUNK_SIZE] for index in range(0, len(text), step) if text[index:index + CHUNK_SIZE].strip()]


def embed(client: httpx.Client, value: str) -> list[float]:
    response = client.post(f"{OLLAMA_BASE_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": value}, timeout=60)
    response.raise_for_status()
    return response.json()["embedding"]


def main() -> None:
    report = {"files": 0, "inserted": 0, "updated": 0, "chunks": 0, "skipped": 0, "embedding_failures": 0}
    with psycopg.connect(DATABASE_URL) as connection, httpx.Client() as client:
        for source in sorted(TRANSCRIPTS.glob("*.md")):
            report["files"] += 1
            metadata, content = parse_source(source)
            digest = hashlib.sha256(content.encode()).hexdigest()
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, content_hash FROM transcripts WHERE source_key = %s", (source.stem,))
                existing = cursor.fetchone()
                if existing and existing[1] == digest:
                    report["skipped"] += 1
                    continue
                if existing:
                    transcript_id = existing[0]
                    cursor.execute("UPDATE transcripts SET episode_title=%s, guest_name=%s, publish_date=%s, source_url=%s, content_hash=%s, ingested_at=NOW() WHERE id=%s", (metadata["title"], metadata.get("guest"), metadata.get("date") or None, metadata["source_url"], digest, transcript_id))
                    cursor.execute("DELETE FROM chunks WHERE transcript_id=%s", (transcript_id,))
                    report["updated"] += 1
                else:
                    cursor.execute("INSERT INTO transcripts (id, source_key, episode_title, guest_name, publish_date, source_url, content_hash) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s) RETURNING id", (source.stem, metadata["title"], metadata.get("guest"), metadata.get("date") or None, metadata["source_url"], digest))
                    transcript_id = cursor.fetchone()[0]
                    report["inserted"] += 1
                for position, value in enumerate(chunks(content)):
                    try:
                        vector = embed(client, value)
                    except (httpx.HTTPError, KeyError) as exc:
                        report["embedding_failures"] += 1
                        print(f"embedding failure in {source.name} chunk {position}: {exc}")
                        continue
                    cursor.execute("INSERT INTO chunks (id, transcript_id, position, text, embedding) VALUES (gen_random_uuid(), %s, %s, %s, %s)", (transcript_id, position, value, json.dumps(vector)))
                    report["chunks"] += 1
        connection.commit()
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
