"""Add FarmerPlot model

Revision ID: 0003_farmer_plots
Revises: 0002_administrative_boundaries
Create Date: 2026-09-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('farmer_plots',
    sa.Column('plot_id', sa.String(length=36), nullable=False, comment='Unique identifier for the agricultural plot'),
    sa.Column('user_id', sa.String(length=100), nullable=False, comment='Identifier for the farmer/user owning the plot'),
    sa.Column('plot_name', sa.String(length=100), nullable=False, comment='Human-readable name of the plot'),
    sa.Column('crop_name', sa.String(length=100), nullable=False, comment='Current crop planted in the plot (e.g. Cotton, Wheat)'),
    sa.Column('area_acres', sa.Numeric(precision=8, scale=2), nullable=True, comment='Area of the plot in acres'),
    sa.Column('centroid_lat', sa.Numeric(precision=8, scale=5), nullable=False, comment='Plot centroid latitude (WGS84)'),
    sa.Column('centroid_lon', sa.Numeric(precision=8, scale=5), nullable=False, comment='Plot centroid longitude (WGS84)'),
    sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False, comment='PostGIS Point geometry in EPSG:4326 for spatial queries'),
    sa.PrimaryKeyConstraint('plot_id')
    )
    op.create_index(op.f('ix_farmer_plots_user_id'), 'farmer_plots', ['user_id'], unique=False)
    op.create_index('idx_farmer_plots_geom', 'farmer_plots', ['geom'], unique=False, postgresql_using='gist')


def downgrade() -> None:
    op.drop_index('idx_farmer_plots_geom', table_name='farmer_plots', postgresql_using='gist')
    op.drop_index(op.f('ix_farmer_plots_user_id'), table_name='farmer_plots')
    op.drop_table('farmer_plots')

