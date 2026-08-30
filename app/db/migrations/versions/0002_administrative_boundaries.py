"""create administrative boundaries tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30 00:00:00.000000

Creates administrative geography hierarchy tables:
  1. spatial_countries (Level 0)
  2. spatial_states (Level 1)
  3. spatial_districts (Level 2)
  4. spatial_subdistricts (Level 3)

Adds EPSG:4326 MultiPolygon geometry columns, GiST spatial indexes, and foreign keys.
"""
from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. spatial_countries
    op.create_table(
        "spatial_countries",
        sa.Column("country_code", sa.String(length=10), nullable=False, comment="ISO 3166-1 alpha-2 or alpha-3 country code (e.g. 'IN')"),
        sa.Column("country_name", sa.String(length=100), nullable=False, comment="Official country name (e.g. 'India')"),
        sa.Column("area_sqkm", sa.Numeric(precision=12, scale=2), nullable=True, comment="Total geographic land area in square kilometers"),
        sa.Column("centroid_lat", sa.Numeric(precision=8, scale=5), nullable=True, comment="Geographic centroid latitude (WGS84)"),
        sa.Column("centroid_lon", sa.Numeric(precision=8, scale=5), nullable=True, comment="Geographic centroid longitude (WGS84)"),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="MultiPolygon", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", spatial_index=False), nullable=False, comment="PostGIS MultiPolygon boundary geometry in EPSG:4326"),
        sa.PrimaryKeyConstraint("country_code"),
    )
    op.create_index("idx_spatial_countries_geom", "spatial_countries", ["geom"], unique=False, postgresql_using="gist")

    # 2. spatial_states
    op.create_table(
        "spatial_states",
        sa.Column("state_code", sa.String(length=10), nullable=False, comment="ISO 3166-2:IN state code (e.g. 'IN-GJ', 'IN-MH')"),
        sa.Column("country_code", sa.String(length=10), nullable=False, server_default="IN", comment="Parent country reference code"),
        sa.Column("state_name", sa.String(length=100), nullable=False, comment="Official state or union territory name"),
        sa.Column("state_type", sa.String(length=30), nullable=False, server_default="State", comment="Administrative type ('State' or 'Union Territory')"),
        sa.Column("area_sqkm", sa.Numeric(precision=10, scale=2), nullable=True, comment="Total state area in square kilometers"),
        sa.Column("centroid_lat", sa.Numeric(precision=8, scale=5), nullable=True, comment="State centroid latitude (WGS84)"),
        sa.Column("centroid_lon", sa.Numeric(precision=8, scale=5), nullable=True, comment="State centroid longitude (WGS84)"),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="MultiPolygon", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", spatial_index=False), nullable=False, comment="PostGIS MultiPolygon boundary geometry in EPSG:4326"),
        sa.ForeignKeyConstraint(["country_code"], ["spatial_countries.country_code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("state_code"),
    )
    op.create_index("idx_spatial_states_geom", "spatial_states", ["geom"], unique=False, postgresql_using="gist")
    op.create_index("idx_spatial_states_country", "spatial_states", ["country_code"], unique=False)

    # 3. spatial_districts
    op.create_table(
        "spatial_districts",
        sa.Column("district_code", sa.String(length=20), nullable=False, comment="Census / LGD / ISO district code (e.g. 'IN-GJ-24')"),
        sa.Column("state_code", sa.String(length=10), nullable=False, comment="Parent state reference code"),
        sa.Column("district_name", sa.String(length=100), nullable=False, comment="Official district name (e.g. 'Surat')"),
        sa.Column("area_sqkm", sa.Numeric(precision=10, scale=2), nullable=True, comment="District area in square kilometers"),
        sa.Column("centroid_lat", sa.Numeric(precision=8, scale=5), nullable=False, comment="District centroid latitude (WGS84)"),
        sa.Column("centroid_lon", sa.Numeric(precision=8, scale=5), nullable=False, comment="District centroid longitude (WGS84)"),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="MultiPolygon", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", spatial_index=False), nullable=False, comment="PostGIS MultiPolygon boundary geometry in EPSG:4326"),
        sa.ForeignKeyConstraint(["state_code"], ["spatial_states.state_code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("district_code"),
    )
    op.create_index("idx_spatial_districts_geom", "spatial_districts", ["geom"], unique=False, postgresql_using="gist")
    op.create_index("idx_spatial_districts_state", "spatial_districts", ["state_code"], unique=False)

    # 4. spatial_subdistricts
    op.create_table(
        "spatial_subdistricts",
        sa.Column("subdistrict_code", sa.String(length=30), nullable=False, comment="LGD / Census sub-district code (e.g. 'IN-GJ-24-001')"),
        sa.Column("district_code", sa.String(length=20), nullable=False, comment="Parent district reference code"),
        sa.Column("subdistrict_name", sa.String(length=100), nullable=False, comment="Official sub-district / tehsil name (e.g. 'Choryasi')"),
        sa.Column("area_sqkm", sa.Numeric(precision=10, scale=2), nullable=True, comment="Sub-district area in square kilometers"),
        sa.Column("centroid_lat", sa.Numeric(precision=8, scale=5), nullable=True, comment="Sub-district centroid latitude (WGS84)"),
        sa.Column("centroid_lon", sa.Numeric(precision=8, scale=5), nullable=True, comment="Sub-district centroid longitude (WGS84)"),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="MultiPolygon", srid=4326, from_text="ST_GeomFromEWKT", name="geometry", spatial_index=False), nullable=False, comment="PostGIS MultiPolygon boundary geometry in EPSG:4326"),
        sa.ForeignKeyConstraint(["district_code"], ["spatial_districts.district_code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("subdistrict_code"),
    )
    op.create_index("idx_spatial_subdistricts_geom", "spatial_subdistricts", ["geom"], unique=False, postgresql_using="gist")
    op.create_index("idx_spatial_subdistricts_district", "spatial_subdistricts", ["district_code"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_spatial_subdistricts_district", table_name="spatial_subdistricts")
    op.drop_index("idx_spatial_subdistricts_geom", table_name="spatial_subdistricts")
    op.drop_table("spatial_subdistricts")

    op.drop_index("idx_spatial_districts_state", table_name="spatial_districts")
    op.drop_index("idx_spatial_districts_geom", table_name="spatial_districts")
    op.drop_table("spatial_districts")

    op.drop_index("idx_spatial_states_country", table_name="spatial_states")
    op.drop_index("idx_spatial_states_geom", table_name="spatial_states")
    op.drop_table("spatial_states")

    op.drop_index("idx_spatial_countries_geom", table_name="spatial_countries")
    op.drop_table("spatial_countries")
