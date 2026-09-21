"""Alert Impact Engine for Vayubodhak (USP Phase 3).

Deterministically translates official meteorological alerts (IMD/NDMA CAP bulletins)
into localized operational impact assessments and prescribed actions:
Official Alert -> Hazard -> Affected Area -> Verified Exposure -> Risk / Impact -> Decision -> Action.

Core Invariants:
1. Zero LLM dependency, 100% deterministic Python mathematics.
2. Official warning severity (Green, Yellow, Orange, Red) is strictly immutable.
3. Incorporates exact H x E x V operational impact formula (docs/11 §4.2).
4. Reversible, traceable audit trail linking CAP Alert ID to NirnayCard.
"""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.contracts.location import LocationContext
from app.decision.models import AlertImpactEvidence, ExposureState
from app.gis.analysis.exposure import calculate_exposure_metrics
from app.gis.analysis.hazards import score_official_alert_hazard
from app.gis.analysis.impact import calculate_operational_impact
from app.gis.analysis.multi_hazard import evaluate_multi_hazard_compounding
from app.gis.analysis.vulnerability import evaluate_district_vulnerability

logger = logging.getLogger(__name__)

# Severity hierarchy for ranking and aggregation
SEVERITY_RANK: Dict[str, int] = {
    "RED": 4,
    "ORANGE": 3,
    "AMBER": 3,
    "YELLOW": 2,
    "GREEN": 1,
    "NONE": 0,
}

# Approximate buffer distance for adjacent/proximity exposure (in km)
BUFFER_PROXIMITY_KM: float = 25.0


class AlertImpactEngine:
    """Deterministic Alert-to-Impact Intelligence Engine."""

    def evaluate_alerts(
        self,
        alerts: List[Dict[str, Any]],
        location: LocationContext,
        query_time_iso: Optional[str] = None,
    ) -> Tuple[List[AlertImpactEvidence], Optional[AlertImpactEvidence]]:
        """Evaluates all candidate official alerts against user location.
        
        Returns:
            Tuple of:
            - List of individual AlertImpactEvidence objects
            - Primary governing AlertImpactEvidence (highest severity inside location,
              or highest regional alert if outside)
        """
        if not alerts:
            return [], None

        now_dt = self._parse_iso(query_time_iso) or datetime.now(timezone.utc)
        evaluations: List[AlertImpactEvidence] = []

        for raw in alerts:
            impact_ev = self.evaluate_single_alert(raw, location, now_dt)
            evaluations.append(impact_ev)

        if not evaluations:
            return [], None

        # Sort evaluations by exposure state (INSIDE first), severity rank (descending), then by composite impact score
        evaluations.sort(
            key=lambda e: (
                1 if e.exposure_state == ExposureState.INSIDE else 0,
                SEVERITY_RANK.get(e.warning_level.upper(), 0),
                e.composite_impact_score,
            ),
            reverse=True,
        )

        primary = evaluations[0]
        return evaluations, primary

    def evaluate_alert(
        self,
        alert_dict: Dict[str, Any],
        location: LocationContext,
        now_dt: Optional[datetime] = None,
    ) -> AlertImpactEvidence:
        """Convenience method to evaluate a single alert with default current time."""
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)
        return self.evaluate_single_alert(alert_dict=alert_dict, location=location, now_dt=now_dt)

    def evaluate_single_alert(
        self,
        alert_dict: Dict[str, Any],
        location: LocationContext,
        now_dt: datetime,
    ) -> AlertImpactEvidence:
        """Evaluates a single official alert for hazard, spatial exposure, and operational impact."""
        alert_id = str(alert_dict.get("alert_id") or alert_dict.get("id") or "OFFICIAL-ALERT-01")
        issuing_office = str(alert_dict.get("sender") or alert_dict.get("issuing_office") or alert_dict.get("source") or alert_dict.get("sender_name") or "Official")
        warning_level = str(alert_dict.get("warning_level") or alert_dict.get("severity") or "Yellow").capitalize()
        if warning_level.upper() == "AMBER":
            warning_level = "Orange"
            
        hazard_type = str(alert_dict.get("hazard_type") or alert_dict.get("hazard") or alert_dict.get("event") or "Severe Weather")
        event_title = str(alert_dict.get("event_title") or alert_dict.get("headline") or alert_dict.get("event") or f"Official {warning_level} Warning")
        description = str(alert_dict.get("description") or alert_dict.get("headline") or "")
        instruction = alert_dict.get("instruction") or alert_dict.get("prescribed_action")
        area_desc = str(alert_dict.get("area_description") or alert_dict.get("area") or alert_dict.get("headline") or "")
        effective_iso = alert_dict.get("effective_time_iso") or alert_dict.get("effective")
        expires_iso = alert_dict.get("expires_time_iso") or alert_dict.get("expires") or alert_dict.get("valid_until")
        
        polygons_raw = alert_dict.get("polygons") or alert_dict.get("polygon") or alert_dict.get("wkt_polygon") or alert_dict.get("area_polygon") or []
        if isinstance(polygons_raw, str):
            polygons_raw = [polygons_raw]
        elif isinstance(polygons_raw, list) and polygons_raw and isinstance(polygons_raw[0], (list, tuple)) and polygons_raw[0] and isinstance(polygons_raw[0][0], (int, float)):
            polygons_raw = [polygons_raw]
        geocodes_raw = alert_dict.get("geocodes") or alert_dict.get("geocode") or []
        if isinstance(geocodes_raw, dict):
            geocodes_raw = [geocodes_raw]

        # 1. Deterministic Hazard Scoring (Immutable Severity)
        hazard_rec = score_official_alert_hazard(warning_level)
        h_score = hazard_rec.hazard_score

        # 2. Spatial Exposure Evaluation
        exposure_state, exp_area_sqkm, exp_area_pct, dist_km = self._evaluate_spatial_exposure(
            polygons=polygons_raw,
            geocodes=geocodes_raw,
            area_description=area_desc,
            location=location,
        )

        # Map exposure state to numeric score E [0.0 - 10.0]
        if exposure_state == ExposureState.INSIDE:
            # Full exposure inside warning perimeter
            e_score = 10.0
            if exp_area_pct > 0.0:
                e_score = min(10.0, max(5.0, exp_area_pct / 10.0))
        elif exposure_state == ExposureState.BUFFER:
            # Proximity buffer exposure
            e_score = 4.0
        elif exposure_state == ExposureState.OUTSIDE:
            # Zero exposure when outside active boundary
            e_score = 0.0
        else:
            e_score = 5.0  # Default nominal for broad unmapped regional alerts

        # 3. Vulnerability Evaluation
        district_id = location.district or getattr(location, "district_code", None) or location.name
        v_eval = evaluate_district_vulnerability(district_code=district_id)
        v_score = v_eval.vulnerability_score

        # 4. Composite Operational Impact Calculation (0.50*H + 0.30*E + 0.20*V)
        # If exposure is strictly OUTSIDE, local impact is mitigated to zero/negligible
        if exposure_state == ExposureState.OUTSIDE:
            impact_res = calculate_operational_impact(
                hazard_score=0.0,
                exposure_score=0.0,
                vulnerability_score=v_score,
            )
        else:
            impact_res = calculate_operational_impact(
                hazard_score=h_score,
                exposure_score=e_score,
                vulnerability_score=v_score,
            )

        # 5. Determine Prescribed Action adhering to warning immutability
        prescribed_action = self._determine_prescribed_action(
            warning_level=warning_level,
            exposure_state=exposure_state,
            hazard_type=hazard_type,
            location=location,
            area_desc=area_desc,
            instruction=instruction,
            issuing_office=issuing_office,
        )

        # 6. Check Active Status
        is_active = True
        if expires_iso:
            exp_dt = self._parse_iso(expires_iso)
            if exp_dt and exp_dt < now_dt:
                is_active = False

        return AlertImpactEvidence(
            alert_id=alert_id,
            issuing_office=issuing_office,
            warning_level=warning_level,
            hazard_type=hazard_type,
            event_title=event_title,
            description=description,
            instruction=instruction,
            effective_time_iso=str(effective_iso) if effective_iso else None,
            expires_time_iso=str(expires_iso) if expires_iso else None,
            area_description=area_desc,
            exposure_state=exposure_state,
            exposed_area_sqkm=exp_area_sqkm,
            exposed_area_pct=exp_area_pct,
            hazard_score=h_score,
            exposure_score=e_score,
            vulnerability_score=v_score,
            composite_impact_score=impact_res.composite_impact_score,
            risk_category=impact_res.risk_category.value if hasattr(impact_res.risk_category, "value") else str(impact_res.risk_category),
            action_priority=impact_res.action_priority,
            prescribed_action=prescribed_action,
            is_official=True,
            is_active=is_active,
            polygons=[str(p) for p in polygons_raw],
            geocodes=geocodes_raw,
        )

    def _evaluate_spatial_exposure(
        self,
        polygons: List[Any],
        geocodes: List[Dict[str, str]],
        area_description: str,
        location: LocationContext,
    ) -> Tuple[ExposureState, float, float, float]:
        """Calculates spatial exposure state, exposed area (km²), percentage, and distance."""
        user_lat = location.latitude
        user_lon = location.longitude
        loc_district = (location.district or location.name or "").strip().lower()
        loc_state = (location.state or "").strip().lower()

        # Strategy 1: Explicit Polygons (Point-in-Polygon & Proximity Buffer)
        parsed_rings = self._parse_polygon_rings(polygons)
        if parsed_rings and user_lat is not None and user_lon is not None:
            # Check containment across all rings
            for ring in parsed_rings:
                if self._point_in_polygon(user_lon, user_lat, ring):
                    area_sqkm = self._approx_polygon_area_sqkm(ring)
                    return ExposureState.INSIDE, area_sqkm, 100.0, 0.0

            # Point is outside rings; calculate closest distance to perimeter
            min_dist_km = min(self._min_distance_to_ring_km(user_lon, user_lat, ring) for ring in parsed_rings)
            if min_dist_km <= BUFFER_PROXIMITY_KM:
                return ExposureState.BUFFER, 0.0, 40.0, min_dist_km
            else:
                return ExposureState.OUTSIDE, 0.0, 0.0, min_dist_km

        # Strategy 2: Administrative District / Geocode Matching
        area_text = area_description.lower()
        geocode_values = [str(v).lower() for g in geocodes for v in g.values()]

        # If administrative geocodes are provided
        if geocode_values:
            if loc_district and any(loc_district in g for g in geocode_values):
                return ExposureState.INSIDE, 2500.0, 100.0, 0.0
            return ExposureState.OUTSIDE, 0.0, 0.0, 100.0

        # Strategy 3: Area Description Text Match (District / State)
        if area_text:
            if loc_district and loc_district in area_text:
                return ExposureState.INSIDE, 2500.0, 100.0, 0.0
            if loc_state and loc_state in area_text:
                return ExposureState.INSIDE, 5000.0, 50.0, 0.0
            # If area description explicitly names specific other districts
            if any(w in area_text for w in ["district", "districts"]):
                return ExposureState.OUTSIDE, 0.0, 0.0, 100.0

        # Fallback: Alert without usable geometry or spatial match: UNKNOWN to prevent fabricated inside/outside result
        return ExposureState.UNKNOWN, 0.0, 0.0, 0.0

    def _determine_prescribed_action(
        self,
        warning_level: str,
        exposure_state: ExposureState,
        hazard_type: str,
        location: LocationContext,
        area_desc: str,
        instruction: Optional[str],
        issuing_office: str = "Official",
    ) -> str:
        """Determines direct, unambiguous operational command conforming to official alert level."""
        loc_name = location.district or location.name or "your area"
        authority = issuing_office if issuing_office and issuing_office.lower() != "official" else "Official"

        if exposure_state == ExposureState.OUTSIDE:
            target_area = area_desc or "neighboring regions"
            return (
                f"Active official {warning_level} Alert is in effect for {target_area}, but spatial verification confirms "
                f"{loc_name} is outside the active warning boundary. Maintain normal monitoring of regional weather bulletins."
            )

        if exposure_state == ExposureState.UNKNOWN:
            target_area = area_desc or "unspecified region"
            return (
                f"Official {warning_level} Alert reported for {target_area}, but spatial geometry is unmapped or unavailable. "
                f"Spatial containment status is UNKNOWN. Maintain heightened vigilance and check local administration bulletins."
            )

        if warning_level.upper() == "RED":
            if instruction:
                return f"EMERGENCY ACTION REQUIRED: {instruction.strip()}"
            return (
                f"TAKE ACTION (EMERGENCY): {authority} Red Alert for {hazard_type} in {loc_name}. "
                f"Suspend all unprotected outdoor and field operations immediately. Move to secure, structurally sound shelter "
                f"and adhere strictly to local district disaster management directives."
            )

        if warning_level.upper() == "ORANGE":
            if instruction:
                return f"BE PREPARED: {instruction.strip()}"
            return (
                f"BE PREPARED (POSTPONE): {authority} Orange Alert for {hazard_type} in {loc_name}. "
                f"Postpone all chemical spraying, irrigation, and non-essential field operations. "
                f"Secure farm implements, livestock, and drainage channels against heavy rain or squally winds."
            )

        if warning_level.upper() == "YELLOW":
            if instruction:
                return f"BE UPDATED: {instruction.strip()}"
            return (
                f"BE UPDATED (WATCH): {authority} Yellow Alert for {hazard_type} in {loc_name}. "
                f"Operations may proceed with caution. Continuously monitor radar and official updates, "
                f"and ensure rapid contingency measures are ready on-site."
            )

        return "NO ADVISORY (GREEN): Normal weather conditions prevailing. Standard operational schedules apply."

    # ========================================================================
    # Spatial Parsing & Ray-Casting Utilities
    # ========================================================================

    def _parse_polygon_rings(self, polygons: List[Any]) -> List[List[Tuple[float, float]]]:
        """Parses CAP polygon strings or GeoJSON geometries into list of (lon, lat) rings."""
        rings: List[List[Tuple[float, float]]] = []

        for p in polygons:
            if isinstance(p, str):
                p_clean = p.strip()
                if p_clean.upper().startswith("POLYGON") or p_clean.upper().startswith("MULTIPOLYGON"):
                    # WKT format: POLYGON((lon lat, lon lat, ...))
                    nums = re.findall(r"[-+]?\d*\.?\d+", p_clean)
                    ring: List[Tuple[float, float]] = []
                    for i in range(0, len(nums) - 1, 2):
                        ring.append((float(nums[i]), float(nums[i + 1])))
                    if len(ring) >= 3:
                        rings.append(ring)
                else:
                    # CAP format: "lat1,lon1 lat2,lon2 lat3,lon3 ..."
                    coords_str = p_clean
                    pairs = re.split(r"[\s]+", coords_str)
                    ring = []
                    for pair in pairs:
                        if "," in pair:
                            parts = pair.split(",")
                            try:
                                lat = float(parts[0].strip())
                                lon = float(parts[1].strip())
                                ring.append((lon, lat))
                            except (ValueError, IndexError):
                                continue
                    if len(ring) >= 3:
                        rings.append(ring)

            elif isinstance(p, dict):
                # GeoJSON Polygon or MultiPolygon
                geom_type = p.get("type", "")
                coords = p.get("coordinates", [])
                if geom_type == "Polygon" and coords:
                    # coords[0] is exterior ring of [lon, lat]
                    exterior = [(float(c[0]), float(c[1])) for c in coords[0] if len(c) >= 2]
                    if len(exterior) >= 3:
                        rings.append(exterior)
                elif geom_type == "MultiPolygon" and coords:
                    for poly in coords:
                        if poly:
                            exterior = [(float(c[0]), float(c[1])) for c in poly[0] if len(c) >= 2]
                            if len(exterior) >= 3:
                                rings.append(exterior)

            elif isinstance(p, list):
                # Direct list of coordinate pairs
                ring: List[Tuple[float, float]] = []
                for item in p:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        ring.append((float(item[0]), float(item[1])))
                if len(ring) >= 3:
                    rings.append(ring)

        return rings

    def _point_in_polygon(self, x: float, y: float, ring: List[Tuple[float, float]]) -> bool:
        """Ray-casting algorithm for 2D point-in-polygon containment test.
        
        Args:
            x: Target longitude
            y: Target latitude
            ring: Sequence of (lon, lat) boundary vertices
        """
        n = len(ring)
        if n < 3:
            return False

        inside = False
        p1x, p1y = ring[0]
        for i in range(1, n + 1):
            p2x, p2y = ring[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _min_distance_to_ring_km(self, lon: float, lat: float, ring: List[Tuple[float, float]]) -> float:
        """Computes minimum approximate distance (km) from point to polygon perimeter segments."""
        n = len(ring)
        if n == 0:
            return float("inf")

        min_dist_km = float("inf")
        cos_lat = math.cos(math.radians(lat))

        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]

            # Segment in km relative to point
            dx1 = (x1 - lon) * 111.0 * cos_lat
            dy1 = (y1 - lat) * 111.0
            dx2 = (x2 - lon) * 111.0 * cos_lat
            dy2 = (y2 - lat) * 111.0

            seg_dx = dx2 - dx1
            seg_dy = dy2 - dy1
            seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy

            if seg_len_sq == 0.0:
                dist = math.sqrt(dx1 * dx1 + dy1 * dy1)
            else:
                t = max(0.0, min(1.0, -(dx1 * seg_dx + dy1 * seg_dy) / seg_len_sq))
                proj_x = dx1 + t * seg_dx
                proj_y = dy1 + t * seg_dy
                dist = math.sqrt(proj_x * proj_x + proj_y * proj_y)

            if dist < min_dist_km:
                min_dist_km = dist

        return min_dist_km

    def _approx_polygon_area_sqkm(self, ring: List[Tuple[float, float]]) -> float:
        """Computes approximate planar area in square kilometers for a polygon ring."""
        n = len(ring)
        if n < 3:
            return 0.0
        # Shoelace formula in degrees, scaled by km per degree
        area_deg2 = 0.0
        for i in range(n):
            j = (i + 1) % n
            area_deg2 += ring[i][0] * ring[j][1]
            area_deg2 -= ring[j][0] * ring[i][1]
        area_deg2 = abs(area_deg2) / 2.0
        avg_lat = sum(p[1] for p in ring) / n
        km_per_lat = 111.0
        km_per_lon = 111.0 * math.cos(math.radians(avg_lat))
        return round(area_deg2 * km_per_lat * km_per_lon, 1)

    def _parse_iso(self, iso_str: Optional[str]) -> Optional[datetime]:
        """Safely parses ISO timestamp string into UTC datetime object."""
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
