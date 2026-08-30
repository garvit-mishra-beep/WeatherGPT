"""Standard Map Legend Metadata Builders."""

from typing import List, Optional
from app.gis.map.styling import OFFICIAL_WARNING_COLORS, RISK_CATEGORY_COLORS
from app.gis.map.types import MapLegendItem


def build_warning_legend(active_severity: Optional[str] = None) -> List[MapLegendItem]:
    """Constructs official warning legend items preserving immutable IMD color codes."""
    items = []
    for sev, info in OFFICIAL_WARNING_COLORS.items():
        if active_severity and sev.lower() != active_severity.lower():
            continue
        items.append(
            MapLegendItem(
                label=f"IMD {sev} Alert",
                color=info["fill"],
                official_level=sev,
            )
        )
    return items


def build_risk_legend() -> List[MapLegendItem]:
    """Constructs operational H x E x V risk category legend items."""
    return [
        MapLegendItem(
            label="Low Risk",
            color=RISK_CATEGORY_COLORS["Low Risk"]["fill"],
            value_range="0.0 - 3.4",
        ),
        MapLegendItem(
            label="Medium Risk",
            color=RISK_CATEGORY_COLORS["Medium Risk"]["fill"],
            value_range="3.5 - 6.9",
        ),
        MapLegendItem(
            label="High / Critical Risk",
            color=RISK_CATEGORY_COLORS["High / Critical Risk"]["fill"],
            value_range="7.0 - 10.0",
        ),
    ]


def build_weather_legend(variable: str = "rain") -> List[MapLegendItem]:
    """Constructs meteorological variable legend."""
    var = variable.lower()
    if "rain" in var or "precip" in var:
        return [
            MapLegendItem(label="Light Rain (< 15.6 mm)", color="#90CDF4"),
            MapLegendItem(label="Moderate Rain (15.6 - 64.4 mm)", color="#4299E1"),
            MapLegendItem(label="Heavy Rain (64.5 - 115.5 mm)", color="#3182CE"),
            MapLegendItem(label="Very Heavy Rain (> 115.5 mm)", color="#2B6CB0"),
        ]
    elif "temp" in var:
        return [
            MapLegendItem(label="Moderate (< 38°C)", color="#FBD38D"),
            MapLegendItem(label="High (38 - 42°C)", color="#ED8936"),
            MapLegendItem(label="Severe Heat (> 42°C)", color="#C53030"),
        ]
    else:
        return [MapLegendItem(label="Surface Observation", color="#805AD5")]
