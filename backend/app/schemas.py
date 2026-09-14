from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    label: str = Field(default="New conversation", max_length=200)
    owner_label: str | None = Field(default=None, max_length=120)


class SessionSummary(BaseModel):
    id: UUID
    label: str
    owner_label: str | None
    created_at: datetime
    last_active_at: datetime


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12_000)


class Citation(BaseModel):
    chunk_id: UUID
    episode_title: str
    guest_name: str | None
    source_url: str


class Message(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    provider: str | None = None
    model_name: str | None = None
    latency_ms: int | None = None
    token_count: int | None = None
    created_at: datetime
    citations: list[Citation] = []


class ArtifactGenerateRequest(BaseModel):
    type: Literal["markdown", "html"] = "markdown"
    prompt: str | None = Field(default=None, max_length=2000)
    message_id: UUID | None = None


class ArtifactResponse(BaseModel):
    id: UUID
    session_id: UUID
    message_id: UUID | None = None
    type: Literal["markdown", "html"]
    content: str
    version: int
    created_at: datetime

