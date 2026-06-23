"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import get_engine
from app.models.base import Base
# Import all models for table creation
import app.models.review_feedback  # noqa: F401 — register RLHF models
from app.api.v1.router import v1_router
from app.api.external.router import external_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    Base.metadata.create_all(bind=get_engine())
    yield


settings = get_settings()

app = FastAPI(
    title="统一上下文管理中心 API",
    description="Context Platform — 公司级统一上下文管理与消费平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (slowapi)
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register routers
app.include_router(v1_router)
app.include_router(external_router)


@app.get("/")
def root():
    return {
        "service": "统一上下文管理中心",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health_check():
    """Simple health check (no DB dependency)."""
    return {"status": "healthy"}
