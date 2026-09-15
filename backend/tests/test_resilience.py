import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.main import app
from app.providers import AnthropicProvider, OllamaProvider, ProviderUnavailable


@pytest.fixture
def client():
    return TestClient(app)


def parse_sse_events(response_text: str) -> list[tuple[str, dict]]:
    events = []
    for block in response_text.strip().split("\n\n"):
        if block:
            event_type = None
            event_data = None
            for line in block.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    event_data = json.loads(line[6:].strip())
            if event_type and event_data is not None:
                events.append((event_type, event_data))
    return events


# Failure Mode 1: Missing API Key
def test_failure_mode_missing_anthropic_api_key():
    settings = Settings(ai_provider="anthropic", anthropic_api_key=None)
    provider = AnthropicProvider(settings)
    with pytest.raises(ProviderUnavailable) as exc_info:
        import asyncio
        asyncio.run(provider.stream([{"role": "user", "content": "hello"}]))
    assert "ANTHROPIC_API_KEY is not configured" in str(exc_info.value)


# Failure Mode 2: Unreachable Ollama
@pytest.mark.asyncio
async def test_failure_mode_unreachable_ollama(monkeypatch):
    settings = Settings(ai_provider="ollama", ollama_base_url="http://invalid-host-unreachable:11434")
    provider = OllamaProvider(settings)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_cm)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

    res = await provider.stream([{"role": "user", "content": "test"}])
    with pytest.raises(ProviderUnavailable) as exc_info:
        async for _ in res.tokens:
            pass
    assert "Local model is unavailable" in str(exc_info.value)


# Failure Mode 3: Model Timeout
@pytest.mark.asyncio
async def test_failure_mode_model_timeout(monkeypatch):
    settings = Settings(ai_provider="ollama", model_timeout_seconds=5.0)
    provider = OllamaProvider(settings)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=httpx.ReadTimeout("Read timed out"))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_cm)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

    res = await provider.stream([{"role": "user", "content": "test"}])
    with pytest.raises(ProviderUnavailable) as exc_info:
        async for _ in res.tokens:
            pass
    assert "timed out" in str(exc_info.value)


# Failure Mode 4: Empty Retrieval Result (Abstention)
def test_failure_mode_empty_retrieval_abstention(client, monkeypatch):
    session_id = uuid4()
    msg_id = uuid4()

    monkeypatch.setattr("app.main.session_exists", lambda s_id: True)
    monkeypatch.setattr("app.main.save_message", lambda s_id, role, content, *args: {
        "id": msg_id, "role": role, "content": content
    })
    monkeypatch.setattr("app.main.retrieve", AsyncMock(return_value=[]))

    res = client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "What is quantum gravity loop theory according to Lenny?"},
    )
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    event_dict = dict(events)

    assert "token" in event_dict
    assert "I don’t have enough supporting material in the available transcript corpus" in event_dict["token"]["text"]
    assert "done" in event_dict
    assert event_dict["done"]["provider"] is None


# Failure Mode 5: Database Connection Failure
def test_failure_mode_database_down_health(client, monkeypatch):
    monkeypatch.setattr("app.main.database_status", lambda: ("down", "OperationalError"))
    res = client.get("/health")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["database"]["status"] == "down"


def test_failure_mode_database_down_during_chat(client, monkeypatch):
    session_id = uuid4()
    monkeypatch.setattr("app.main.session_exists", lambda s_id: True)
    monkeypatch.setattr("app.main.save_message", MagicMock(side_effect=OperationalError("connection down", None, None)))

    res = client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "Hello Lenny"},
    )
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    event_types = [e[0] for e in events]
    assert "error" in event_types
    error_data = next(e[1] for e in events if e[0] == "error")
    assert error_data["code"] == "database_unavailable"
