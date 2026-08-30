"""Central v1 API router.

Single registration point for all ``/api/v1`` sub-routers. New feature routers
(chat, weather, farmer, research, gis, nwp) are included here as they are
implemented, keeping the API prefix centralized.
"""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.farmer import router as farmer_router
from app.api.v1.gis import router as gis_router
from app.api.v1.map import router as map_router
from app.api.v1.nwp import router as nwp_router
from app.api.v1.research import router as research_router
from app.api.v1.system import router as system_router
from app.api.v1.weather import router as weather_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(chat_router)
api_router.include_router(weather_router)
api_router.include_router(farmer_router)
api_router.include_router(research_router)
api_router.include_router(gis_router)
api_router.include_router(map_router)
api_router.include_router(nwp_router)

