import json
from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy import text

from app.config import Settings
from app.database import get_engine
from app.providers import ProviderUnavailable


@dataclass(frozen=True)
class RetrievedChunk:
    id: UUID
    text: str
    episode_title: str
    guest_name: str | None
    source_url: str
    distance: float


async def embed_query(query: str, settings: Settings) -> list[float]:
    try:
        async with httpx.AsyncClient(timeout=settings.model_timeout_seconds) as client:
            response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/embeddings", json={"model": settings.embedding_model, "prompt": query})
            response.raise_for_status()
            return response.json()["embedding"]
    except httpx.TimeoutException as exc:
        raise ProviderUnavailable(f"Embedding request timed out after {settings.model_timeout_seconds}s. Start Ollama and check model load.") from exc
    except (httpx.HTTPError, KeyError) as exc:
        raise ProviderUnavailable("Local embedding model is unavailable. Start Ollama and pull nomic-embed-text.") from exc


async def retrieve(query: str, settings: Settings) -> list[RetrievedChunk]:
    vector = json.dumps(await embed_query(query, settings))
    sql = text("""
        SELECT c.id, c.text, t.episode_title, t.guest_name, t.source_url,
               c.embedding <=> CAST(:embedding AS vector) AS distance
        FROM chunks c JOIN transcripts t ON t.id = c.transcript_id
        WHERE c.embedding <=> CAST(:embedding AS vector) <= :threshold
        ORDER BY distance ASC LIMIT :limit
    """)
    with get_engine().connect() as connection:
        rows = connection.execute(sql, {"embedding": vector, "threshold": settings.retrieval_distance_threshold, "limit": settings.max_retrieved_chunks}).mappings()
        return [RetrievedChunk(**row) for row in rows]


def context_prompt(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"Source: {item.episode_title} | {item.guest_name or 'Unknown guest'} | {item.source_url}\n{item.text}" for item in chunks)
