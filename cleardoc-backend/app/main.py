import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.cache import close_redis, init_redis
from app.config import settings
from app.database import Base, engine
from app.middleware.rate_limiter import rate_limit_middleware
from app.middleware.request_id import request_id_middleware
from app.middleware.security import SecurityMiddleware
from app.models import Document, Reminder, Result, User  # noqa: F401
from app.routers import compare, explain, followup, health, history, reminders

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("cleardoc_starting")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        await init_redis()
    except Exception as exc:  # pragma: no cover - startup resilience
        logger.warning("redis_unavailable", error=str(exc))

    logger.info("cleardoc_ready")
    yield

    await close_redis()
    await engine.dispose()
    logger.info("cleardoc_shutdown")


app = FastAPI(
    title="ClearDoc API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
)

allowed_origins = {
    settings.frontend_url,
    "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://localhost:3847",
    "https://localhost:3847",
    "http://127.0.0.1:3847",
    "https://127.0.0.1:3847",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining-Minute"],
)

app.add_middleware(SecurityMiddleware)
app.middleware("http")(request_id_middleware)
app.middleware("http")(rate_limit_middleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong. Please try again."},
    )


app.include_router(explain.router)
app.include_router(history.router)
app.include_router(followup.router)
app.include_router(reminders.router)
app.include_router(compare.router)
app.include_router(health.router)
