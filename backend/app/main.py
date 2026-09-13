import time
import uuid

from fastapi import FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.logging import configure_logging

logger = configure_logging()
app = FastAPI(title="Lenny Growth Assistant", version="0.1.0")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request.completed", extra={"request_id": request_id, "route": request.url.path, "method": request.method, "status_code": response.status_code, "latency_ms": round((time.perf_counter() - started) * 1000), "provider": get_settings().ai_provider})
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
    return {"status": "ok" if db_state == "up" else "degraded", "dependencies": {"database": {"status": db_state, "detail": detail}}}


@app.get("/config")
def config():
    settings = get_settings()
    model = settings.ollama_model if settings.ai_provider == "ollama" else settings.anthropic_model
    return {"provider": settings.ai_provider, "model": model, "fallback_provider": settings.fallback_provider}
