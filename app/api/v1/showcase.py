"""Internal Showcase Scenario Controller Endpoints.

Provides internal, headless endpoints to drive the demonstration scenario:
- POST /api/v1/internal/showcase/start -> Ingests baseline weather and executes initial pipeline
- POST /api/v1/internal/showcase/next  -> Advances to precipitation escalation / warning update
- POST /api/v1/internal/showcase/reset -> Clears scenario state back to clean baseline
- GET  /api/v1/internal/showcase/status -> Returns current scenario timeline position
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.showcase.runner import showcase_runner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/showcase", tags=["Internal Showcase Controller"])


class ShowcaseActionResponse(BaseModel):
    status: str
    step_index: int
    step_name: Optional[str] = None
    event_id: Optional[str] = None
    sequence_number: Optional[int] = None
    revision_id: Optional[str] = None
    revision_number: Optional[int] = None
    verdict: Optional[str] = None
    severity: Optional[str] = None
    details: Dict[str, Any] = {}


@router.post("/start", response_model=Dict[str, Any])
async def start_showcase() -> Dict[str, Any]:
    """Starts or re-initializes the showcase scenario at Step 0 (Baseline)."""
    return await showcase_runner.start()


@router.post("/next", response_model=Dict[str, Any])
async def next_showcase_step() -> Dict[str, Any]:
    """Advances the showcase scenario to the next chronological step."""
    return await showcase_runner.next()


@router.post("/reset", response_model=Dict[str, Any])
async def reset_showcase() -> Dict[str, Any]:
    """Resets all scenario repositories and sync cursors back to clean state."""
    return await showcase_runner.reset()


@router.get("/status", response_model=Dict[str, Any])
def get_showcase_status() -> Dict[str, Any]:
    """Returns current operational status of the showcase scenario."""
    return showcase_runner.get_status()
