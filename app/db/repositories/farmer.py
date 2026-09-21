"""Farmer Plot repository for Phase 7 alert intersection."""

from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.farmer import FarmerPlot
from app.db.repositories.base import BaseRepository


class FarmerPlotRepository(BaseRepository[FarmerPlot]):
    """Repository for managing Farmer plots and spatial queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=FarmerPlot)

    async def create_plot(
        self,
        user_id: str,
        plot_name: str,
        crop_name: str,
        centroid_lat: float,
        centroid_lon: float,
        area_acres: Optional[float] = None,
    ) -> FarmerPlot:
        """Creates a new farmer plot with spatial geometry."""
        
        # WKT string for Point
        wkt_geom = f"SRID=4326;POINT({centroid_lon} {centroid_lat})"
        
        plot = FarmerPlot(
            plot_id=str(uuid.uuid4()),
            user_id=user_id,
            plot_name=plot_name,
            crop_name=crop_name,
            area_acres=area_acres,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            geom=wkt_geom,
        )
        self.session.add(plot)
        await self.session.commit()
        await self.session.refresh(plot)
        return plot

    async def get_by_user(self, user_id: str) -> List[FarmerPlot]:
        """Retrieves all plots for a given user."""
        stmt = select(FarmerPlot).where(FarmerPlot.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_plots_in_polygon(self, wkt_polygon: str) -> List[FarmerPlot]:
        """Finds all farmer plots that intersect with a given PostGIS Polygon (WKT).
        
        Args:
            wkt_polygon: WKT string of the polygon (e.g. 'SRID=4326;POLYGON(...)')
            
        Returns:
            List of FarmerPlot objects contained/intersecting the polygon.
        """
        # We use ST_Intersects against the point geometry.
        # wkt_polygon should be provided as SRID=4326
        from sqlalchemy import func
        
        if not wkt_polygon.startswith("SRID="):
            wkt_polygon = f"SRID=4326;{wkt_polygon}"
            
        stmt = select(FarmerPlot).where(
            func.ST_Intersects(
                FarmerPlot.geom,
                func.ST_GeomFromEWKT(wkt_polygon)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
