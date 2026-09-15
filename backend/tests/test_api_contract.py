import json
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.providers import ProviderResponse
from app.retrieval import RetrievedChunk


async def mock_async_tokens(tokens: list[str]):
    for t in tokens:
        yield t


@pytest.fixture
def client():
    return TestClient(app)


def test_api_contract_sessions_crud(client, monkeypatch):
    session_id = uuid4()
    mock_sessions = [
        {
            "id": session_id,
            "label": "Growth activation discussion",
            "owner_label": "Priya",
            "created_at": "2026-09-15T10:00:00Z",
            "last_active_at": "2026-09-15T10:05:00Z",
        }
    ]

    monkeypatch.setattr("app.main.list_sessions", lambda: mock_sessions)
    monkeypatch.setattr("app.main.create_session", lambda label, owner: {
        "id": session_id,
        "label": label or "New Session",
        "owner_label": owner or "Evaluator",
        "created_at": "2026-09-15T10:00:00Z",
        "last_active_at": "2026-09-15T10:00:00Z",
    })
    monkeypatch.setattr("app.main.delete_session", lambda s_id: s_id == session_id)
    monkeypatch.setattr("app.main.session_exists", lambda s_id: s_id == session_id)

    # 1. POST /sessions
    res_post = client.post("/sessions", json={"label": "Growth activation discussion", "owner_label": "Priya"})
    assert res_post.status_code == 201
    created = res_post.json()
    assert created["id"] == str(session_id)
    assert created["label"] == "Growth activation discussion"
    assert created["owner_label"] == "Priya"

    # 2. GET /sessions
    res_get = client.get("/sessions")
    assert res_get.status_code == 200
    assert isinstance(res_get.json(), list)
    assert len(res_get.json()) == 1

    # 3. DELETE /sessions/{id}
    res_del = client.delete(f"/sessions/{session_id}")
    assert res_del.status_code == 204

    # 4. DELETE /sessions/nonexistent -> 404
    res_del_404 = client.delete(f"/sessions/{uuid4()}")
    assert res_del_404.status_code == 404


def test_api_contract_messages(client, monkeypatch):
    session_id = uuid4()
    msg_id = uuid4()
    mock_messages = [
        {
            "id": msg_id,
            "session_id": session_id,
            "role": "user",
            "content": "What is the aha moment in onboarding?",
            "created_at": "2026-09-15T10:01:00Z",
            "provider": None,
            "model_name": None,
            "latency_ms": None,
            "citations": [],
        },
        {
            "id": uuid4(),
            "session_id": session_id,
            "role": "assistant",
            "content": "The aha moment is when a user first experiences the core product value.",
            "created_at": "2026-09-15T10:01:02Z",
            "provider": "ollama",
            "model_name": "qwen2.5:7b",
            "latency_ms": 1200,
            "citations": [
                {
                    "id": uuid4(),
                    "chunk_id": uuid4(),
                    "episode_title": "Onboarding Masterclass",
                    "guest_name": "Elena Verna",
                    "source_url": "https://lenny.com/elena",
                }
            ],
        },
    ]

    monkeypatch.setattr("app.main.session_exists", lambda s_id: s_id == session_id)
    monkeypatch.setattr("app.main.message_history", lambda s_id: mock_messages if s_id == session_id else [])

    res = client.get(f"/sessions/{session_id}/messages")
    assert res.status_code == 200
    msgs = res.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["provider"] == "ollama"
    assert len(msgs[1]["citations"]) == 1

    # Non-existent session
    res_404 = client.get(f"/sessions/{uuid4()}/messages")
    assert res_404.status_code == 404


def test_api_contract_chat_sse_stream(client, monkeypatch):
    session_id = uuid4()
    msg_id = uuid4()

    monkeypatch.setattr("app.main.session_exists", lambda s_id: True)
    monkeypatch.setattr("app.main.save_message", lambda s_id, role, content, *args: {
        "id": msg_id, "role": role, "content": content
    })
    monkeypatch.setattr("app.main.save_citations", lambda m_id, chunks: None)
    monkeypatch.setattr("app.main.message_history", lambda s_id: [])

    chunk = RetrievedChunk(
        id=uuid4(),
        text="Onboarding activation must focus on early user success.",
        episode_title="Activation Benchmarks",
        guest_name="Elena Verna",
        source_url="https://lenny.com/activation",
        distance=0.2,
    )
    monkeypatch.setattr("app.main.retrieve", AsyncMock(return_value=[chunk]))

    mock_provider = AsyncMock()
    mock_provider.stream.return_value = ProviderResponse(
        provider="ollama",
        model="qwen2.5:7b",
        tokens=mock_async_tokens(["Activation ", "focuses on ", "onboarding time-to-value."]),
    )
    monkeypatch.setattr("app.main.provider_for", lambda name, settings: mock_provider)

    res = client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "How should teams improve user activation?"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    events = []
    lines = res.text.strip().split("\n\n")
    for block in lines:
        if block:
            event_type = None
            event_data = None
            for line in block.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    event_data = json.loads(line[6:])
            if event_type:
                events.append((event_type, event_data))

    event_types = [e[0] for e in events]
    assert "intent" in event_types
    assert "token" in event_types
    assert "citations" in event_types
    assert "done" in event_types
