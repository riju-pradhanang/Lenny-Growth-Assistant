import json
import time
import uuid
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.essay_skill import build_essay_system_prompt, validate_essay_structure
from app.logging import configure_logging
from app.providers import ProviderUnavailable, provider_for
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
from app.retrieval import context_prompt, retrieve
from app.router import classify_intent
from app.sanitizer import sanitize_html
from app.schemas import ArtifactGenerateRequest, ArtifactResponse, ChatRequest, SessionCreate

logger = configure_logging()
app = FastAPI(title="Lenny Growth Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.completed",
        extra={
            "request_id": request_id,
            "route": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "provider": get_settings().ai_provider,
        },
    )
    return response


def database_status() -> tuple[str, str | None]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return "up", None
    except SQLAlchemyError as exc:
        return "down", type(exc).__name__


@app.get("/health")
def health(response: Response):
    db_state, detail = database_status()
    if db_state != "up":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if db_state == "up" else "degraded",
        "dependencies": {"database": {"status": db_state, "detail": detail}},
    }


@app.get("/config")
def config():
    settings = get_settings()
    model = settings.ollama_model if settings.ai_provider == "ollama" else settings.anthropic_model
    return {
        "provider": settings.ai_provider,
        "model": model,
        "fallback_provider": settings.fallback_provider,
    }


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def new_session(payload: SessionCreate):
    return create_session(payload.label, payload.owner_label)


@app.get("/sessions")
def sessions():
    return list_sessions()


@app.get("/sessions/{session_id}/messages")
def messages(session_id: UUID):
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    return message_history(session_id)


@app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_session(session_id: UUID):
    if not delete_session(session_id):
        raise HTTPException(404, "Session not found")
    return Response(status_code=204)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/sessions/{session_id}/chat")
async def chat(session_id: UUID, payload: ChatRequest):
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    settings = get_settings()
    save_message(session_id, "user", payload.content)

    async def response_stream():
        started = time.perf_counter()
        try:
            intent = classify_intent(payload.content)
            yield sse("intent", {"intent": intent})

            chunks = await retrieve(payload.content, settings)
            if not chunks:
                answer = "I don’t have enough supporting material in the available transcript corpus to answer that reliably. Try rephrasing or asking about a topic covered by the curated sources."
                saved = save_message(session_id, "assistant", answer)
                yield sse("token", {"text": answer})
                yield sse("done", {"message_id": str(saved["id"]), "provider": None, "intent": intent})
                return

            history = [{"role": item["role"], "content": item["content"]} for item in message_history(session_id)[-8:]]

            if intent == "essay":
                system_content = build_essay_system_prompt(chunks)
            else:
                system_content = (
                    "Answer only from the supplied source excerpts. If they are insufficient, say so. "
                    "Cite the named sources in your prose.\n\n" + context_prompt(chunks)
                )

            history.insert(0, {"role": "system", "content": system_content})

            selected = settings.ai_provider
            try:
                result = await provider_for(selected, settings).stream(history)
            except ProviderUnavailable:
                if not settings.fallback_provider:
                    raise
                result = await provider_for(settings.fallback_provider, settings).stream(history)

            answer = ""
            try:
                async for token in result.tokens:
                    answer += token
                    yield sse("token", {"text": token})
            except ProviderUnavailable:
                # A fallback is safe only before the primary has emitted user-visible text.
                if answer or not settings.fallback_provider:
                    raise
                result = await provider_for(settings.fallback_provider, settings).stream(history)
                async for token in result.tokens:
                    answer += token
                    yield sse("token", {"text": token})

            # For essays, validate structural requirements
            validation_data = None
            if intent == "essay":
                val = validate_essay_structure(answer)
                validation_data = val.to_dict()
                yield sse("validation", validation_data)

            saved = save_message(
                session_id,
                "assistant",
                answer,
                result.provider,
                result.model,
                round((time.perf_counter() - started) * 1000),
            )
            save_citations(saved["id"], chunks)
            yield sse(
                "citations",
                {
                    "items": [
                        {
                            "chunk_id": str(item.id),
                            "episode_title": item.episode_title,
                            "guest_name": item.guest_name,
                            "source_url": item.source_url,
                        }
                        for item in chunks
                    ]
                },
            )
            yield sse(
                "done",
                {
                    "message_id": str(saved["id"]),
                    "provider": result.provider,
                    "model": result.model,
                    "intent": intent,
                    "validation": validation_data,
                },
            )
        except ProviderUnavailable as exc:
            logger.warning("chat.provider_unavailable", extra={"provider": settings.ai_provider})
            yield sse("error", {"code": "provider_unavailable", "message": str(exc)})
        except SQLAlchemyError:
            yield sse(
                "error",
                {
                    "code": "database_unavailable",
                    "message": "Conversation could not be saved because the database is unavailable.",
                },
            )

    return StreamingResponse(response_stream(), media_type="text/event-stream")


@app.post("/sessions/{session_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def generate_artifact(session_id: UUID, payload: ArtifactGenerateRequest):
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    settings = get_settings()

    # Determine context source
    target_content = ""
    target_message_id = payload.message_id
    if target_message_id:
        msg = get_message(target_message_id)
        if msg:
            target_content = msg["content"]

    if not target_content:
        # Use latest assistant message in the session
        hist = message_history(session_id)
        assistant_msgs = [m for m in hist if m["role"] == "assistant"]
        if assistant_msgs:
            latest = assistant_msgs[-1]
            target_content = latest["content"]
            target_message_id = latest["id"]
        else:
            target_content = "No previous conversation context available."

    prompt_detail = payload.prompt or "Format the key insights and actionable takeaways as a standalone document."

    if payload.type == "html":
        system_prompt = (
            "You are a frontend design and formatting specialist. Turn the supplied insights into a beautiful, "
            "self-contained, modern HTML/CSS card or dashboard widget snippet. "
            "Use clean inline CSS or a scoped <style> block with rich typography, subtle card borders, and tags. "
            "DO NOT use external script tags or unsafe event handlers. Output ONLY the HTML content."
        )
    else:
        system_prompt = (
            "You are an expert technical editor. Turn the supplied insights into a clean, structured Markdown artifact "
            "with a title, key highlights, tables/checklists if appropriate, and bullet points. Output ONLY the Markdown."
        )

    messages_payload = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{target_content}\n\nTask: {prompt_detail}"},
    ]

    selected = settings.ai_provider
    try:
        provider = provider_for(selected, settings)
        stream_res = await provider.stream(messages_payload)
    except ProviderUnavailable:
        if not settings.fallback_provider:
            raise HTTPException(503, "Configured model provider is unavailable.")
        provider = provider_for(settings.fallback_provider, settings)
        stream_res = await provider.stream(messages_payload)

    generated_text = ""
    async for token in stream_res.tokens:
        generated_text += token

    # Sanitize if HTML
    if payload.type == "html":
        final_content = sanitize_html(generated_text)
    else:
        final_content = generated_text.strip()

    artifact = save_artifact(
        session_id=session_id,
        artifact_type=payload.type,
        content=final_content,
        message_id=target_message_id,
    )
    return artifact


@app.get("/sessions/{session_id}/artifacts", response_model=list[ArtifactResponse])
def get_session_artifacts(session_id: UUID):
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    return list_artifacts_for_session(session_id)


@app.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_single_artifact(artifact_id: UUID):
    artifact = get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    return artifact
