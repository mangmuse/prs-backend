import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware.sessions import SessionMiddleware

from src.auth.router import router as auth_router
from src.common.types import HealthResponse
from src.config import get_settings
from src.datasets.router import router as datasets_router
from src.llm.router import router as llm_router
from src.profiles.router import router as profiles_router
from src.prompts.router import router as prompts_router
from src.runs.router import router as runs_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(llm_router)
app.include_router(profiles_router)
app.include_router(prompts_router)
app.include_router(runs_router)


@app.get("/health")
async def health_check() -> HealthResponse:
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}
