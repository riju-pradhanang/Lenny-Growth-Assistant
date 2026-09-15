from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.config import Settings
from app.retrieval import RetrievedChunk, context_prompt, embed_query, retrieve


@pytest.mark.asyncio
async def test_embed_query_success(monkeypatch):
    settings = Settings(ollama_base_url="http://mock-ollama:11434", embedding_model="nomic-embed-text")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

    result = await embed_query("how to grow b2b saas", settings)
    assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_retrieve_chunks_filtering(monkeypatch):
    settings = Settings(retrieval_distance_threshold=0.8, max_retrieved_chunks=3)
    
    # Mock embed_query
    monkeypatch.setattr("app.retrieval.embed_query", AsyncMock(return_value=[0.1, 0.2, 0.3]))

    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()
    mock_rows = [
        {
            "id": chunk_id_1,
            "text": "Product market fit is when retention curves flatten.",
            "episode_title": "Finding PMF",
            "guest_name": "Casey Winters",
            "source_url": "https://lenny.com/casey",
            "distance": 0.25,
        },
        {
            "id": chunk_id_2,
            "text": "Cohort analysis confirms if true retention exists.",
            "episode_title": "Finding PMF",
            "guest_name": "Casey Winters",
            "source_url": "https://lenny.com/casey",
            "distance": 0.45,
        },
    ]

    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value = mock_rows
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    monkeypatch.setattr("app.retrieval.get_engine", lambda: mock_engine)

    chunks = await retrieve("retention curve analysis", settings)
    assert len(chunks) == 2
    assert chunks[0].id == chunk_id_1
    assert chunks[0].distance == 0.25
    assert chunks[1].id == chunk_id_2

    # Verify context_prompt formatting
    prompt = context_prompt(chunks)
    assert "Finding PMF" in prompt
    assert "Casey Winters" in prompt
    assert "Product market fit is when retention curves flatten." in prompt
