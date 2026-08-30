"""Spatial boundary repositories for PostgreSQL + PostGIS administrative hierarchy.

Provides statically-typed, async data access for Countries, States, Districts,
and Sub-Districts, with PostGIS ``ST_Contains`` spatial lookups and idempotent upserts.
"""

import json
from typing import Any, Dict, List, Optional, Sequence

from geoalchemy2.functions import ST_Contains, ST_GeomFromGeoJSON, ST_Point, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.db.repositories.base import BaseRepository
from app.db.spatial import SRID_4326


class CountryRepository(BaseRepository[SpatialCountry]):
    """Repository for country administrative boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SpatialCountry)

    async def get_by_code(self, country_code: str) -> Optional[SpatialCountry]:
        return await self.get(country_code.strip().upper())

    async def find_containing_point(self, lat: float, lon: float) -> Optional[SpatialCountry]:
        """Return the country polygon containing the (lat, lon) coordinates."""
        point_geom = ST_SetSRID(ST_Point(lon, lat), SRID_4326)
        stmt = select(SpatialCountry).where(ST_Contains(SpatialCountry.geom, point_geom)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, data: Dict[str, Any]) -> SpatialCountry:
        """Idempotently insert or update a country boundary."""
        geom_geojson = json.dumps(data["geom"]) if isinstance(data["geom"], dict) else data["geom"]
        geom_expr = ST_SetSRID(ST_GeomFromGeoJSON(geom_geojson), SRID_4326)

        stmt = (
            pg_insert(SpatialCountry)
            .values(
                country_code=data["country_code"],
                country_name=data["country_name"],
                area_sqkm=data.get("area_sqkm"),
                centroid_lat=data.get("centroid_lat"),
                centroid_lon=data.get("centroid_lon"),
                geom=geom_expr,
            )
            .on_conflict_do_update(
                index_elements=["country_code"],
                set_={
                    "country_name": data["country_name"],
                    "area_sqkm": data.get("area_sqkm"),
                    "centroid_lat": data.get("centroid_lat"),
                    "centroid_lon": data.get("centroid_lon"),
                    "geom": geom_expr,
                },
            )
            .returning(SpatialCountry)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one()


class StateRepository(BaseRepository[SpatialState]):
    """Repository for state / UT administrative boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SpatialState)

    async def get_by_code(self, state_code: str) -> Optional[SpatialState]:
        return await self.get(state_code.strip().upper())

    async def list_by_country(self, country_code: str = "IN") -> Sequence[SpatialState]:
        stmt = select(SpatialState).where(SpatialState.country_code == country_code.upper()).order_by(SpatialState.state_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_containing_point(self, lat: float, lon: float) -> Optional[SpatialState]:
        """Return the state polygon containing the (lat, lon) coordinates."""
        point_geom = ST_SetSRID(ST_Point(lon, lat), SRID_4326)
        stmt = select(SpatialState).where(ST_Contains(SpatialState.geom, point_geom)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, data: Dict[str, Any]) -> SpatialState:
        """Idempotently insert or update a state boundary."""
        geom_geojson = json.dumps(data["geom"]) if isinstance(data["geom"], dict) else data["geom"]
        geom_expr = ST_SetSRID(ST_GeomFromGeoJSON(geom_geojson), SRID_4326)

        stmt = (
            pg_insert(SpatialState)
            .values(
                state_code=data["state_code"],
                country_code=data.get("country_code", "IN"),
                state_name=data["state_name"],
                state_type=data.get("state_type", "State"),
                area_sqkm=data.get("area_sqkm"),
                centroid_lat=data.get("centroid_lat"),
                centroid_lon=data.get("centroid_lon"),
                geom=geom_expr,
            )
            .on_conflict_do_update(
                index_elements=["state_code"],
                set_={
                    "country_code": data.get("country_code", "IN"),
                    "state_name": data["state_name"],
                    "state_type": data.get("state_type", "State"),
                    "area_sqkm": data.get("area_sqkm"),
                    "centroid_lat": data.get("centroid_lat"),
                    "centroid_lon": data.get("centroid_lon"),
                    "geom": geom_expr,
                },
            )
            .returning(SpatialState)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one()


class DistrictRepository(BaseRepository[SpatialDistrict]):
    """Repository for district administrative boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SpatialDistrict)

    async def get_by_code(self, district_code: str) -> Optional[SpatialDistrict]:
        return await self.get(district_code.strip().upper())

    async def list_by_state(self, state_code: str) -> Sequence[SpatialDistrict]:
        stmt = (
            select(SpatialDistrict)
            .where(SpatialDistrict.state_code == state_code.upper())
            .order_by(SpatialDistrict.district_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_containing_point(self, lat: float, lon: float) -> Optional[SpatialDistrict]:
        """Return the district polygon containing the (lat, lon) coordinates."""
        point_geom = ST_SetSRID(ST_Point(lon, lat), SRID_4326)
        stmt = select(SpatialDistrict).where(ST_Contains(SpatialDistrict.geom, point_geom)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, data: Dict[str, Any]) -> SpatialDistrict:
        """Idempotently insert or update a district boundary."""
        geom_geojson = json.dumps(data["geom"]) if isinstance(data["geom"], dict) else data["geom"]
        geom_expr = ST_SetSRID(ST_GeomFromGeoJSON(geom_geojson), SRID_4326)

        stmt = (
            pg_insert(SpatialDistrict)
            .values(
                district_code=data["district_code"],
                state_code=data["state_code"],
                district_name=data["district_name"],
                area_sqkm=data.get("area_sqkm"),
                centroid_lat=data["centroid_lat"],
                centroid_lon=data["centroid_lon"],
                geom=geom_expr,
            )
            .on_conflict_do_update(
                index_elements=["district_code"],
                set_={
                    "state_code": data["state_code"],
                    "district_name": data["district_name"],
                    "area_sqkm": data.get("area_sqkm"),
                    "centroid_lat": data["centroid_lat"],
                    "centroid_lon": data["centroid_lon"],
                    "geom": geom_expr,
                },
            )
            .returning(SpatialDistrict)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one()


class SubDistrictRepository(BaseRepository[SpatialSubDistrict]):
    """Repository for sub-district / tehsil administrative boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SpatialSubDistrict)

    async def get_by_code(self, subdistrict_code: str) -> Optional[SpatialSubDistrict]:
        return await self.get(subdistrict_code.strip().upper())

    async def list_by_district(self, district_code: str) -> Sequence[SpatialSubDistrict]:
        stmt = (
            select(SpatialSubDistrict)
            .where(SpatialSubDistrict.district_code == district_code.upper())
            .order_by(SpatialSubDistrict.subdistrict_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_containing_point(self, lat: float, lon: float) -> Optional[SpatialSubDistrict]:
        """Return the sub-district polygon containing the (lat, lon) coordinates."""
        point_geom = ST_SetSRID(ST_Point(lon, lat), SRID_4326)
        stmt = select(SpatialSubDistrict).where(ST_Contains(SpatialSubDistrict.geom, point_geom)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, data: Dict[str, Any]) -> SpatialSubDistrict:
        """Idempotently insert or update a sub-district boundary."""
        geom_geojson = json.dumps(data["geom"]) if isinstance(data["geom"], dict) else data["geom"]
        geom_expr = ST_SetSRID(ST_GeomFromGeoJSON(geom_geojson), SRID_4326)

        stmt = (
            pg_insert(SpatialSubDistrict)
            .values(
                subdistrict_code=data["subdistrict_code"],
                district_code=data["district_code"],
                subdistrict_name=data["subdistrict_name"],
                area_sqkm=data.get("area_sqkm"),
                centroid_lat=data.get("centroid_lat"),
                centroid_lon=data.get("centroid_lon"),
                geom=geom_expr,
            )
            .on_conflict_do_update(
                index_elements=["subdistrict_code"],
                set_={
                    "district_code": data["district_code"],
                    "subdistrict_name": data["subdistrict_name"],
                    "area_sqkm": data.get("area_sqkm"),
                    "centroid_lat": data.get("centroid_lat"),
                    "centroid_lon": data.get("centroid_lon"),
                    "geom": geom_expr,
                },
            )
            .returning(SpatialSubDistrict)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one()
