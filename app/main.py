"""WeatherGPT FastAPI Application Entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle setup and teardown."""
    logger.info("Initializing %s (%s environment)...", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Domain-grounded conversational weather decision-intelligence platform for India.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint providing application status and environment details."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider_type,
        "llm_model": settings.llm_model_name,
    }


@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
async def root() -> Dict[str, Any]:
    """Root metadata endpoint."""
    return {
        "message": "Welcome to WeatherGPT API",
        "docs_url": "/docs",
        "health_url": "/health",
        "version": "0.1.0",
    }
