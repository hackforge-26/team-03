import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.cache import init_redis, close_redis
from app.middleware.rate_limiter import rate_limit_middleware
from app.middleware.request_id import request_id_middleware
from app.routers import explain, history, followup, reminders, compare, health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("cleardoc_starting")

    # Create all database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Connect to Redis
    await init_redis()

    logger.info("cleardoc_ready")
    yield

    # SHUTDOWN
    await close_redis()
    await engine.dispose()
    logger.info("cleardoc_shutdown")


app = FastAPI(
    title="ClearDoc API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
)

# CORS — only your Stitch frontend can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Request ID Middleware
app.middleware("http")(request_id_middleware)

# Rate Limiter Middleware
app.middleware("http")(rate_limit_middleware)


# Global Error Handler — never expose internal errors to client
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


# Routers
app.include_router(explain.router)
app.include_router(history.router)
app.include_router(followup.router)
app.include_router(reminders.router)
app.include_router(compare.router)
app.include_router(health.router)
