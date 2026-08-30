"""Administrative boundary ORM models (India, States, Districts, Sub-Districts).

Implements the administrative hierarchy defined in ``docs/09_GIS_SPEC.md`` and
``docs/10_DATABASE_SCHEMA.md``:

    SpatialCountry (Level 0: India)
         ↓
    SpatialState   (Level 1: States / Union Territories)
         ↓
    SpatialDistrict (Level 2: Districts)
         ↓
    SpatialSubDistrict (Level 3: Tehsils / Talukas / Mandals)

All spatial columns use PostGIS MultiPolygon in **EPSG:4326** (WGS84).
Foreign key constraints preserve hierarchy integrity directly in PostgreSQL.
"""

from typing import List, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.spatial import MultiPolygon


class SpatialCountry(Base):
    """Country level administrative boundary (Level 0).

    Example:
        country_code: 'IN'
        country_name: 'India'
    """

    __tablename__ = "spatial_countries"

    country_code: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="ISO 3166-1 alpha-2 or alpha-3 country code (e.g. 'IN')",
    )
    country_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Official country name (e.g. 'India')",
    )
    area_sqkm: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total geographic land area in square kilometers",
    )
    centroid_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="Geographic centroid latitude (WGS84)",
    )
    centroid_lon: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="Geographic centroid longitude (WGS84)",
    )
    geom = mapped_column(
        MultiPolygon,
        nullable=False,
        comment="PostGIS MultiPolygon boundary geometry in EPSG:4326",
    )

    # Relationships
    states: Mapped[List["SpatialState"]] = relationship(
        "SpatialState",
        back_populates="country",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SpatialCountry(code={self.country_code!r}, name={self.country_name!r})>"


class SpatialState(Base):
    """State / Union Territory administrative boundary (Level 1).

    Example:
        state_code: 'IN-GJ'
        state_name: 'Gujarat'
        state_type: 'State'
    """

    __tablename__ = "spatial_states"

    state_code: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="ISO 3166-2:IN state code (e.g. 'IN-GJ', 'IN-MH')",
    )
    country_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("spatial_countries.country_code", ondelete="RESTRICT"),
        nullable=False,
        default="IN",
        index=True,
        comment="Parent country reference code",
    )
    state_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Official state or union territory name",
    )
    state_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="State",
        comment="Administrative type ('State' or 'Union Territory')",
    )
    area_sqkm: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total state area in square kilometers",
    )
    centroid_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="State centroid latitude (WGS84)",
    )
    centroid_lon: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="State centroid longitude (WGS84)",
    )
    geom = mapped_column(
        MultiPolygon,
        nullable=False,
        comment="PostGIS MultiPolygon boundary geometry in EPSG:4326",
    )

    # Relationships
    country: Mapped["SpatialCountry"] = relationship(
        "SpatialCountry",
        back_populates="states",
    )
    districts: Mapped[List["SpatialDistrict"]] = relationship(
        "SpatialDistrict",
        back_populates="state",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SpatialState(code={self.state_code!r}, name={self.state_name!r})>"


class SpatialDistrict(Base):
    """District administrative boundary (Level 2).

    Example:
        district_code: 'IN-GJ-24'
        state_code: 'IN-GJ'
        district_name: 'Surat'
    """

    __tablename__ = "spatial_districts"

    district_code: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        comment="Census / LGD / ISO district code (e.g. 'IN-GJ-24')",
    )
    state_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("spatial_states.state_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Parent state reference code",
    )
    district_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Official district name (e.g. 'Surat')",
    )
    area_sqkm: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="District area in square kilometers",
    )
    centroid_lat: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="District centroid latitude (WGS84)",
    )
    centroid_lon: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="District centroid longitude (WGS84)",
    )
    geom = mapped_column(
        MultiPolygon,
        nullable=False,
        comment="PostGIS MultiPolygon boundary geometry in EPSG:4326",
    )

    # Relationships
    state: Mapped["SpatialState"] = relationship(
        "SpatialState",
        back_populates="districts",
    )
    subdistricts: Mapped[List["SpatialSubDistrict"]] = relationship(
        "SpatialSubDistrict",
        back_populates="district",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SpatialDistrict(code={self.district_code!r}, name={self.district_name!r})>"


class SpatialSubDistrict(Base):
    """Sub-District / Tehsil / Taluka administrative boundary (Level 3).

    Example:
        subdistrict_code: 'IN-GJ-24-001'
        district_code: 'IN-GJ-24'
        subdistrict_name: 'Choryasi'
    """

    __tablename__ = "spatial_subdistricts"

    subdistrict_code: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        comment="LGD / Census sub-district code (e.g. 'IN-GJ-24-001')",
    )
    district_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("spatial_districts.district_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Parent district reference code",
    )
    subdistrict_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Official sub-district / tehsil name (e.g. 'Choryasi')",
    )
    area_sqkm: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Sub-district area in square kilometers",
    )
    centroid_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="Sub-district centroid latitude (WGS84)",
    )
    centroid_lon: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 5),
        nullable=True,
        comment="Sub-district centroid longitude (WGS84)",
    )
    geom = mapped_column(
        MultiPolygon,
        nullable=False,
        comment="PostGIS MultiPolygon boundary geometry in EPSG:4326",
    )

    # Relationships
    district: Mapped["SpatialDistrict"] = relationship(
        "SpatialDistrict",
        back_populates="subdistricts",
    )

    def __repr__(self) -> str:
        return f"<SpatialSubDistrict(code={self.subdistrict_code!r}, name={self.subdistrict_name!r})>"
