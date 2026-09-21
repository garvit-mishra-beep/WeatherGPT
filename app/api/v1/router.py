"""Central v1 API router.

Single registration point for all ``/api/v1`` sub-routers. New feature routers
(chat, weather, farmer, research, gis, nwp) are included here as they are
implemented, keeping the API prefix centralized.
"""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.climate import router as climate_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.farmer import router as farmer_router
from app.api.v1.gis import router as gis_router
from app.api.v1.map import router as map_router
from app.api.v1.nwp import router as nwp_router
from app.api.v1.research import router as research_router
from app.api.v1.system import router as system_router
from app.api.v1.voice import router as voice_router
from app.api.v1.weather import router as weather_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analyst import router as analyst_router
from app.api.v1.proactive import router as proactive_router
from app.api.v1.personalization import router as personalization_router
from app.evidence.router import router as evidence_router
from app.hazard.router import hazard_router
from app.exposure.router import exposure_router
from app.vulnerability.router import router as vulnerability_router
from app.risk.router import router as risk_router
from app.impact.router import router as impact_router
from app.api.v1.data_sources import router as data_sources_router
from app.api.v1.sync import router as sync_router
from app.decision.router import router as decision_router
from app.pipeline.router import router as pipeline_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(chat_router)
api_router.include_router(decisions_router)
api_router.include_router(climate_router)
api_router.include_router(voice_router)
api_router.include_router(weather_router)
api_router.include_router(farmer_router)
api_router.include_router(research_router)
api_router.include_router(gis_router)
api_router.include_router(analyst_router)
api_router.include_router(map_router)
api_router.include_router(nwp_router)
api_router.include_router(alerts_router)
api_router.include_router(proactive_router)
api_router.include_router(personalization_router)
api_router.include_router(evidence_router)
api_router.include_router(hazard_router)
api_router.include_router(exposure_router)
api_router.include_router(vulnerability_router)
api_router.include_router(risk_router)
api_router.include_router(impact_router)
api_router.include_router(decision_router)
api_router.include_router(pipeline_router)
from app.api.v1.showcase import router as showcase_router

api_router.include_router(data_sources_router)
api_router.include_router(sync_router)
api_router.include_router(showcase_router)


