from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.providers import ProviderResponse


async def mock_async_tokens(tokens: list[str]):
    for t in tokens:
        yield t


def test_artifact_generation_and_retrieval(monkeypatch):
    client = TestClient(app)

    # Mock session exists and repository functions
    session_id = uuid4()
    artifact_id = uuid4()
    
    mock_artifact = {
        "id": artifact_id,
        "session_id": session_id,
        "message_id": None,
        "type": "html",
        "content": "<div class=\"widget\"><h2>Activation Strategy</h2><p>Focus on onboarding time-to-value.</p></div>",
        "version": 1,
        "created_at": "2026-09-15T00:00:00Z"
    }

    monkeypatch.setattr("app.main.session_exists", lambda s_id: True)
    monkeypatch.setattr("app.main.message_history", lambda s_id: [{"id": uuid4(), "role": "assistant", "content": "Sample insight content"}])
    monkeypatch.setattr("app.main.save_artifact", lambda session_id, artifact_type, content, message_id: {
        **mock_artifact,
        "type": artifact_type,
        "content": content
    })
    monkeypatch.setattr("app.main.get_artifact", lambda a_id: mock_artifact if a_id == artifact_id else None)
    monkeypatch.setattr("app.main.list_artifacts_for_session", lambda s_id: [mock_artifact])

    # Mock provider stream
    raw_html_output = '<div><h2>Activation Strategy</h2><script>alert("hack")</script><p>Focus on onboarding time-to-value.</p></div>'
    mock_provider = AsyncMock()
    mock_provider.stream.return_value = ProviderResponse(
        provider="ollama",
        model="llama3.1:8b",
        tokens=mock_async_tokens([raw_html_output])
    )
    monkeypatch.setattr("app.main.provider_for", lambda name, settings: mock_provider)

    # 1. Test POST /sessions/{id}/artifacts
    post_res = client.post(
        f"/sessions/{session_id}/artifacts",
        json={"type": "html", "prompt": "Create an activation widget"}
    )
    assert post_res.status_code == 201
    data = post_res.json()
    assert data["type"] == "html"
    # Verify script tag was stripped by sanitizer
    assert "<script>" not in data["content"]
    assert "alert" not in data["content"]
    assert "<h2>Activation Strategy</h2>" in data["content"]

    # 2. Test GET /sessions/{id}/artifacts
    list_res = client.get(f"/sessions/{session_id}/artifacts")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Test GET /artifacts/{id}
    get_res = client.get(f"/artifacts/{artifact_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == str(artifact_id)
