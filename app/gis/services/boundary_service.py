"""Administrative Boundary Service for hierarchical GIS lookups and reverse-geocoding."""

import logging
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.gis.repositories.boundaries import (
    CountryRepository,
    DistrictRepository,
    StateRepository,
    SubDistrictRepository,
)
from app.gis.schemas.boundaries import (
    AdminLevel,
    BoundarySummary,
    HierarchyResolutionResult,
)

logger = logging.getLogger(__name__)


class AdministrativeBoundaryService:
    """Service providing spatial point-in-polygon resolution and hierarchy traversal."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.countries = CountryRepository(session)
        self.states = StateRepository(session)
        self.districts = DistrictRepository(session)
        self.subdistricts = SubDistrictRepository(session)

    async def resolve_location(self, lat: float, lon: float) -> HierarchyResolutionResult:
        """Resolve point coordinates (lat, lon) to enclosing country, state, district, subdistrict.

        Executes spatial point-in-polygon queries against PostGIS GiST-indexed geometries.
        """
        # Concurrent / sequential resolution
        country_obj = await self.countries.find_containing_point(lat, lon)
        state_obj = await self.states.find_containing_point(lat, lon)
        district_obj = await self.districts.find_containing_point(lat, lon)
        subdistrict_obj = await self.subdistricts.find_containing_point(lat, lon)

        country_summary = (
            BoundarySummary(
                code=country_obj.country_code,
                name=country_obj.country_name,
                level=AdminLevel.COUNTRY,
                area_sqkm=float(country_obj.area_sqkm) if country_obj.area_sqkm is not None else None,
                centroid_lat=float(country_obj.centroid_lat) if country_obj.centroid_lat is not None else None,
                centroid_lon=float(country_obj.centroid_lon) if country_obj.centroid_lon is not None else None,
            )
            if country_obj
            else None
        )

        state_summary = (
            BoundarySummary(
                code=state_obj.state_code,
                name=state_obj.state_name,
                level=AdminLevel.STATE,
                parent_code=state_obj.country_code,
                area_sqkm=float(state_obj.area_sqkm) if state_obj.area_sqkm is not None else None,
                centroid_lat=float(state_obj.centroid_lat) if state_obj.centroid_lat is not None else None,
                centroid_lon=float(state_obj.centroid_lon) if state_obj.centroid_lon is not None else None,
            )
            if state_obj
            else None
        )

        district_summary = (
            BoundarySummary(
                code=district_obj.district_code,
                name=district_obj.district_name,
                level=AdminLevel.DISTRICT,
                parent_code=district_obj.state_code,
                area_sqkm=float(district_obj.area_sqkm) if district_obj.area_sqkm is not None else None,
                centroid_lat=float(district_obj.centroid_lat) if district_obj.centroid_lat is not None else None,
                centroid_lon=float(district_obj.centroid_lon) if district_obj.centroid_lon is not None else None,
            )
            if district_obj
            else None
        )

        subdistrict_summary = (
            BoundarySummary(
                code=subdistrict_obj.subdistrict_code,
                name=subdistrict_obj.subdistrict_name,
                level=AdminLevel.SUBDISTRICT,
                parent_code=subdistrict_obj.district_code,
                area_sqkm=float(subdistrict_obj.area_sqkm) if subdistrict_obj.area_sqkm is not None else None,
                centroid_lat=float(subdistrict_obj.centroid_lat) if subdistrict_obj.centroid_lat is not None else None,
                centroid_lon=float(subdistrict_obj.centroid_lon) if subdistrict_obj.centroid_lon is not None else None,
            )
            if subdistrict_obj
            else None
        )

        resolved = (state_summary is not None) and (district_summary is not None)

        return HierarchyResolutionResult(
            latitude=lat,
            longitude=lon,
            country=country_summary,
            state=state_summary,
            district=district_summary,
            subdistrict=subdistrict_summary,
            resolved=resolved,
        )

    async def get_state(self, state_code: str) -> Optional[BoundarySummary]:
        st = await self.states.get_by_code(state_code)
        if not st:
            return None
        return BoundarySummary(
            code=st.state_code,
            name=st.state_name,
            level=AdminLevel.STATE,
            parent_code=st.country_code,
            area_sqkm=float(st.area_sqkm) if st.area_sqkm is not None else None,
            centroid_lat=float(st.centroid_lat) if st.centroid_lat is not None else None,
            centroid_lon=float(st.centroid_lon) if st.centroid_lon is not None else None,
        )

    async def get_district(self, district_code: str) -> Optional[BoundarySummary]:
        dt = await self.districts.get_by_code(district_code)
        if not dt:
            return None
        return BoundarySummary(
            code=dt.district_code,
            name=dt.district_name,
            level=AdminLevel.DISTRICT,
            parent_code=dt.state_code,
            area_sqkm=float(dt.area_sqkm) if dt.area_sqkm is not None else None,
            centroid_lat=float(dt.centroid_lat) if dt.centroid_lat is not None else None,
            centroid_lon=float(dt.centroid_lon) if dt.centroid_lon is not None else None,
        )

    async def list_states(self) -> Sequence[BoundarySummary]:
        all_states = await self.states.list_by_country("IN")
        return [
            BoundarySummary(
                code=st.state_code,
                name=st.state_name,
                level=AdminLevel.STATE,
                parent_code=st.country_code,
                area_sqkm=float(st.area_sqkm) if st.area_sqkm is not None else None,
                centroid_lat=float(st.centroid_lat) if st.centroid_lat is not None else None,
                centroid_lon=float(st.centroid_lon) if st.centroid_lon is not None else None,
            )
            for st in all_states
        ]

    async def list_districts_for_state(self, state_code: str) -> Sequence[BoundarySummary]:
        all_districts = await self.districts.list_by_state(state_code)
        return [
            BoundarySummary(
                code=dt.district_code,
                name=dt.district_name,
                level=AdminLevel.DISTRICT,
                parent_code=dt.state_code,
                area_sqkm=float(dt.area_sqkm) if dt.area_sqkm is not None else None,
                centroid_lat=float(dt.centroid_lat) if dt.centroid_lat is not None else None,
                centroid_lon=float(dt.centroid_lon) if dt.centroid_lon is not None else None,
            )
            for dt in all_districts
        ]
