from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from app.repository import (
    create_session,
    delete_session,
    get_artifact,
    get_message,
    list_artifacts_for_session,
    list_sessions,
    message_history,
    save_artifact,
    save_citations,
    save_message,
    session_exists,
)
from app.retrieval import RetrievedChunk


def test_session_lifecycle(monkeypatch):
    session_id = uuid4()
    
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    # 1. create_session
    mock_conn.execute.return_value.mappings.return_value.one.return_value = {
        "id": session_id,
        "label": "Pricing Discussion",
        "owner_label": "Priya",
        "created_at": "2026-09-15T00:00:00Z",
        "last_active_at": "2026-09-15T00:00:00Z",
    }
    monkeypatch.setattr("app.repository.get_engine", lambda: mock_engine)

    created = create_session("Pricing Discussion", "Priya")
    assert created["id"] == session_id
    assert created["label"] == "Pricing Discussion"

    # 2. session_exists
    mock_conn.execute.return_value.scalar.return_value = 1
    assert session_exists(session_id) is True

    # 3. list_sessions
    mock_conn.execute.return_value.mappings.return_value.all.return_value = [created]
    sessions = list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id

    # 4. delete_session
    mock_conn.execute.return_value.rowcount = 1
    assert delete_session(session_id) is True


def test_message_and_citations_persistence(monkeypatch):
    session_id = uuid4()
    msg_id = uuid4()

    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    monkeypatch.setattr("app.repository.get_engine", lambda: mock_engine)

    # 1. save_message
    mock_conn.execute.return_value.mappings.return_value.one.return_value = {
        "id": msg_id,
        "session_id": session_id,
        "role": "assistant",
        "content": "Good pricing begins with value metrics.",
        "provider": "ollama",
        "model_name": "qwen2.5:7b",
        "latency_ms": 1100,
        "token_count": 42,
        "created_at": "2026-09-15T00:00:00Z",
    }

    saved = save_message(session_id, "assistant", "Good pricing begins with value metrics.", "ollama", "qwen2.5:7b", 1100)
    assert saved["id"] == msg_id
    assert saved["role"] == "assistant"

    # 2. save_citations
    chunk = RetrievedChunk(
        id=uuid4(),
        text="Value metrics align pricing with customer outcome.",
        episode_title="Monetization Frameworks",
        guest_name="Patrick Campbell",
        source_url="https://lenny.com/patrick",
        distance=0.1,
    )
    save_citations(msg_id, [chunk])
    assert mock_conn.execute.called

    # 3. message_history with citations
    mock_conn.execute.return_value.mappings.return_value.all.side_effect = [
        # First call: messages
        [
            {
                "id": msg_id,
                "session_id": session_id,
                "role": "assistant",
                "content": "Good pricing begins with value metrics.",
                "created_at": "2026-09-15T00:00:00Z",
                "provider": "ollama",
                "model_name": "qwen2.5:7b",
                "latency_ms": 1100,
            }
        ]
    ]

    history = message_history(session_id)
    assert len(history) == 1
    assert history[0]["id"] == msg_id
    assert history[0]["content"] == "Good pricing begins with value metrics."
    assert history[0]["provider"] == "ollama"
