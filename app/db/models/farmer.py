"""Farmer and agricultural plot ORM models.

Implements the FarmerPlot registry used for spatial alert intersections
and real-time push notification pipelines (USP Phase 7).
"""

from typing import Optional
import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.spatial import Point


class FarmerPlot(Base):
    """Farmer Plot registry for spatial intersection with CAP alerts.

    Example:
        plot_id: 'uuid'
        user_id: 'usr_123'
        plot_name: 'North Field'
        crop_name: 'Cotton'
    """

    __tablename__ = "farmer_plots"

    plot_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the agricultural plot",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Identifier for the farmer/user owning the plot",
    )
    plot_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name of the plot",
    )
    crop_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Current crop planted in the plot (e.g. Cotton, Wheat)",
    )
    area_acres: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Area of the plot in acres",
    )
    centroid_lat: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="Plot centroid latitude (WGS84)",
    )
    centroid_lon: Mapped[float] = mapped_column(
        Numeric(8, 5),
        nullable=False,
        comment="Plot centroid longitude (WGS84)",
    )
    geom = mapped_column(
        Point,
        nullable=False,
        comment="PostGIS Point geometry in EPSG:4326 for spatial queries",
    )

    def __repr__(self) -> str:
        return f"<FarmerPlot(id={self.plot_id!r}, crop={self.crop_name!r}, user={self.user_id!r})>"
