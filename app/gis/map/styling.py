"""Declarative MapLibre GL & Leaflet Styling Specifications."""

from typing import Any, Dict


# ============================================================================
# 1. Official Warning Styling (STRICTLY IMMUTABLE)
# ============================================================================

OFFICIAL_WARNING_COLORS = {
    "Green": {"fill": "#38A169", "opacity": 0.35, "stroke": "#276749"},
    "Yellow": {"fill": "#ECC94B", "opacity": 0.40, "stroke": "#D69E2E"},
    "Orange": {"fill": "#ED8936", "opacity": 0.45, "stroke": "#DD6B20"},
    "Red": {"fill": "#E53E3E", "opacity": 0.55, "stroke": "#9B2C2C"},
}


def get_official_warning_paint(severity: str) -> Dict[str, Any]:
    """Returns declarative fill paint dictionary for official warnings."""
    clean = severity.strip().capitalize()
    color_info = OFFICIAL_WARNING_COLORS.get(clean, OFFICIAL_WARNING_COLORS["Yellow"])
    return {
        "fill-color": color_info["fill"],
        "fill-opacity": color_info["opacity"],
        "fill-outline-color": color_info["stroke"],
    }


# ============================================================================
# 2. Analytical Risk Tier Styling
# ============================================================================

RISK_CATEGORY_COLORS = {
    "Low Risk": {"fill": "#48BB78", "opacity": 0.30, "stroke": "#2F855A"},
    "Medium Risk": {"fill": "#ECC94B", "opacity": 0.40, "stroke": "#D69E2E"},
    "High / Critical Risk": {"fill": "#E53E3E", "opacity": 0.50, "stroke": "#9B2C2C"},
}


def get_analytical_risk_paint(risk_category: str) -> Dict[str, Any]:
    """Returns declarative fill paint for analytical H x E x V risk tiers."""
    color_info = RISK_CATEGORY_COLORS.get(risk_category, RISK_CATEGORY_COLORS["Low Risk"])
    return {
        "fill-color": color_info["fill"],
        "fill-opacity": color_info["opacity"],
        "fill-outline-color": color_info["stroke"],
    }


# ============================================================================
# 3. Administrative Boundary Styling
# ============================================================================

def get_administrative_boundary_paint(level: str = "district") -> Dict[str, Any]:
    """Returns declarative line paint for administrative boundaries."""
    lvl = level.lower()
    if lvl == "state":
        return {"line-color": "#2D3748", "line-width": 2.5}
    elif lvl == "subdistrict":
        return {"line-color": "#718096", "line-width": 1.0, "line-dasharray": [2, 1]}
    else:  # district
        return {"line-color": "#4A5568", "line-width": 1.5}


# ============================================================================
# 4. Weather & Meteorological Point Styling
# ============================================================================

def get_weather_point_paint(variable: str = "temperature") -> Dict[str, Any]:
    """Returns declarative circle paint for weather station markers."""
    var = variable.lower()
    if "rain" in var or "precip" in var:
        return {"circle-color": "#3182CE", "circle-radius": 6.0, "circle-stroke-width": 1.5, "circle-stroke-color": "#2B6CB0"}
    elif "wind" in var:
        return {"circle-color": "#805AD5", "circle-radius": 6.0, "circle-stroke-width": 1.5, "circle-stroke-color": "#553C9A"}
    else:  # temperature
        return {"circle-color": "#DD6B20", "circle-radius": 6.0, "circle-stroke-width": 1.5, "circle-stroke-color": "#C05621"}
