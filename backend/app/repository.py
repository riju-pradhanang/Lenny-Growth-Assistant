from uuid import UUID
from sqlalchemy import text
from app.database import get_engine


def create_session(label: str, owner_label: str | None):
    with get_engine().begin() as conn:
        return conn.execute(text("INSERT INTO sessions (id, label, owner_label) VALUES (gen_random_uuid(), :label, :owner) RETURNING id, label, owner_label, created_at, last_active_at"), {"label": label, "owner": owner_label}).mappings().one()


def list_sessions():
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT id, label, owner_label, created_at, last_active_at FROM sessions ORDER BY last_active_at DESC")).mappings().all()


def session_exists(session_id: UUID) -> bool:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT 1 FROM sessions WHERE id=:id"), {"id": session_id}).first() is not None


def save_message(session_id: UUID, role: str, content: str, provider: str | None = None, model: str | None = None, latency_ms: int | None = None):
    with get_engine().begin() as conn:
        row = conn.execute(text("INSERT INTO messages (id, session_id, role, content, provider, model_name, latency_ms) VALUES (gen_random_uuid(), :session_id, :role, :content, :provider, :model, :latency) RETURNING id, role, content, provider, model_name, latency_ms, token_count, created_at"), {"session_id": session_id, "role": role, "content": content, "provider": provider, "model": model, "latency": latency_ms}).mappings().one()
        conn.execute(text("UPDATE sessions SET last_active_at=NOW() WHERE id=:id"), {"id": session_id})
        return row


def message_history(session_id: UUID):
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT id, role, content, provider, model_name, latency_ms, token_count, created_at FROM messages WHERE session_id=:id ORDER BY created_at"), {"id": session_id}).mappings().all()


def save_citations(message_id: UUID, chunks):
    with get_engine().begin() as conn:
        for item in chunks:
            conn.execute(text("INSERT INTO citations (id, message_id, chunk_id, episode_title, guest_name, source_url) VALUES (gen_random_uuid(), :message_id, :chunk_id, :title, :guest, :url)"), {"message_id": message_id, "chunk_id": item.id, "title": item.episode_title, "guest": item.guest_name, "url": item.source_url})


def delete_session(session_id: UUID) -> bool:
    with get_engine().begin() as conn:
        return conn.execute(text("DELETE FROM sessions WHERE id=:id"), {"id": session_id}).rowcount == 1
