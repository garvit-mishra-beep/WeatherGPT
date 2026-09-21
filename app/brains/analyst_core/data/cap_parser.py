"""OASIS / WMO Common Alerting Protocol (CAP v1.2) Parser and Ingestor.

Converts standard CAP XML and JSON feeds into verified OfficialAlert objects.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json

from app.brains.analyst_core.models.schemas import AlertSeverity, DataType
from app.brains.analyst_core.models.weather_data import OfficialAlert


class CAPParser:
    """Parses standard Common Alerting Protocol (CAP v1.2) alert payloads."""

    CAP_NAMESPACES = {
        "cap": "urn:oasis:names:tc:emergency:cap:1.2",
        "cap11": "urn:oasis:names:tc:emergency:cap:1.1",
    }

    SEVERITY_MAP = {
        "extreme": AlertSeverity.RED_WARNING,
        "severe": AlertSeverity.ORANGE_ALERT,
        "moderate": AlertSeverity.YELLOW_WATCH,
        "minor": AlertSeverity.GREEN_NO_WARNING,
        "unknown": AlertSeverity.YELLOW_WATCH,
    }

    RECOGNIZED_AUTHORITIES = [
        "india meteorological department",
        "imd",
        "national disaster management authority",
        "ndma",
        "national weather service",
        "noaa",
        "wmo",
        "central water commission",
        "cwc",
    ]

    def parse_cap_xml(self, xml_content: str) -> List[OfficialAlert]:
        """Parses CAP XML payload into OfficialAlert models."""
        alerts: List[OfficialAlert] = []
        if not xml_content or not xml_content.strip():
            return alerts

        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError:
            return alerts

        # Check root or namespaced elements
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag[root.tag.find("{") : root.tag.find("}") + 1]

        def get_text(elem, tag: str, default: str = "") -> str:
            sub = elem.find(f"{ns}{tag}")
            return sub.text.strip() if sub is not None and sub.text else default

        identifier = get_text(root, "identifier", "CAP-UNKNOWN-ID")
        sender = get_text(root, "sender", "Official Meteorological Service")
        status = get_text(root, "status", "Actual").lower()
        msg_type = get_text(root, "msgType", "Alert").lower()
        sent_str = get_text(root, "sent", "")

        # Skip test or draft alerts
        if status in {"test", "exercise", "draft"}:
            return alerts

        # Parse issue timestamp
        try:
            issue_time = datetime.fromisoformat(sent_str.replace("Z", "+00:00")) if sent_str else datetime.now(timezone.utc).replace(tzinfo=None)
        except ValueError:
            issue_time = datetime.now(timezone.utc).replace(tzinfo=None)

        info_elements = root.findall(f"{ns}info")
        for info in info_elements:
            event = get_text(info, "event", "Severe Weather")
            urgency = get_text(info, "urgency", "Expected")
            severity_str = get_text(info, "severity", "Moderate").lower()
            certainty = get_text(info, "certainty", "Likely")
            headline = get_text(info, "headline", f"Official Warning: {event}")
            description = get_text(info, "description", "")
            instruction = get_text(info, "instruction", "")

            onset_str = get_text(info, "onset", "")
            expires_str = get_text(info, "expires", "")

            try:
                valid_from = datetime.fromisoformat(onset_str.replace("Z", "+00:00")) if onset_str else issue_time
            except ValueError:
                valid_from = issue_time

            try:
                valid_to = datetime.fromisoformat(expires_str.replace("Z", "+00:00")) if expires_str else issue_time
            except ValueError:
                valid_to = issue_time

            # Area description and polygon coordinates
            area_elem = info.find(f"{ns}area")
            area_desc = get_text(area_elem, "areaDesc", "All Monitored Sectors") if area_elem is not None else "General Region"
            coords = []
            bounds = None
            if area_elem is not None:
                poly_str = get_text(area_elem, "polygon", "")
                if poly_str:
                    try:
                        pairs = poly_str.strip().split()
                        for p in pairs:
                            if "," in p:
                                lat_s, lon_s = p.split(",", 1)
                                coords.append((float(lat_s.strip()), float(lon_s.strip())))
                        if coords:
                            lats = [c[0] for c in coords]
                            lons = [c[1] for c in coords]
                            bounds = (min(lats), min(lons), max(lats), max(lons))
                    except Exception:
                        pass

            # Detect storm ID if present in parameters, eventCode, or text
            storm_id = None
            for param in info.findall(f"{ns}parameter"):
                p_name = get_text(param, "valueName", "").lower()
                if "storm" in p_name or "cyclone" in p_name:
                    storm_id = get_text(param, "value", "")

            mapped_severity = self.SEVERITY_MAP.get(severity_str, AlertSeverity.YELLOW_WATCH)

            # Split instructions into precautions
            precautions = [p.strip() for p in instruction.split(".") if p.strip()] if instruction else []

            # Determine whether authority is recognized
            sender_lower = sender.lower()
            is_verified = any(auth in sender_lower for auth in self.RECOGNIZED_AUTHORITIES) or "official" in sender_lower or "met" in sender_lower

            alerts.append(
                OfficialAlert(
                    alert_id=identifier,
                    issuing_authority=sender,
                    warning_type=event.upper().replace(" ", "_"),
                    severity=mapped_severity,
                    issue_time=issue_time if not issue_time.tzinfo else issue_time.astimezone(timezone.utc).replace(tzinfo=None),
                    valid_from=valid_from if not valid_from.tzinfo else valid_from.astimezone(timezone.utc).replace(tzinfo=None),
                    valid_to=valid_to if not valid_to.tzinfo else valid_to.astimezone(timezone.utc).replace(tzinfo=None),
                    geographic_area=area_desc,
                    headline=headline,
                    description=description,
                    recommended_precautions=precautions,
                    is_verified=is_verified,
                    is_synthetic=False,
                    data_type=DataType.OFFICIAL_WARNING,
                    polygon_coordinates=coords if coords else None,
                    affected_bounds=bounds,
                    storm_id=storm_id,
                )
            )

        return alerts

    def parse_cap_json(self, json_data: Dict[str, Any]) -> List[OfficialAlert]:
        """Parses CAP JSON format (e.g. from NDMA/WMO REST feeds)."""
        alerts = []
        identifier = json_data.get("identifier", "CAP-JSON-ID")
        sender = json_data.get("sender", "India Meteorological Department (IMD)")
        status = json_data.get("status", "Actual").lower()

        if status in {"test", "exercise", "draft"}:
            return alerts

        sent_str = json_data.get("sent", "")
        try:
            issue_time = datetime.fromisoformat(sent_str.replace("Z", "+00:00")) if sent_str else datetime.now(timezone.utc).replace(tzinfo=None)
        except ValueError:
            issue_time = datetime.now(timezone.utc).replace(tzinfo=None)

        info_list = json_data.get("info", [])
        if isinstance(info_list, dict):
            info_list = [info_list]

        for info in info_list:
            event = info.get("event", "Hazard Warning")
            severity_str = info.get("severity", "Moderate").lower()
            headline = info.get("headline", f"Official Advisory: {event}")
            description = info.get("description", "")
            instruction = info.get("instruction", "")
            area_info = info.get("area", {}) if isinstance(info.get("area"), dict) else {}
            area_desc = area_info.get("areaDesc", "Monitored Region")

            coords = []
            bounds = None
            poly_raw = area_info.get("polygon")
            if isinstance(poly_raw, str):
                try:
                    for p in poly_raw.strip().split():
                        if "," in p:
                            lat_s, lon_s = p.split(",", 1)
                            coords.append((float(lat_s.strip()), float(lon_s.strip())))
                    if coords:
                        lats = [c[0] for c in coords]
                        lons = [c[1] for c in coords]
                        bounds = (min(lats), min(lons), max(lats), max(lons))
                except Exception:
                    pass
            elif isinstance(poly_raw, list):
                try:
                    coords = [(float(c[0]), float(c[1])) for c in poly_raw if len(c) >= 2]
                    if coords:
                        lats = [c[0] for c in coords]
                        lons = [c[1] for c in coords]
                        bounds = (min(lats), min(lons), max(lats), max(lons))
                except Exception:
                    pass

            storm_id = info.get("storm_id") or json_data.get("storm_id")
            precautions = [p.strip() for p in instruction.split(".") if p.strip()] if instruction else []
            mapped_severity = self.SEVERITY_MAP.get(severity_str, AlertSeverity.YELLOW_WATCH)

            alerts.append(
                OfficialAlert(
                    alert_id=identifier,
                    issuing_authority=sender,
                    warning_type=event.upper().replace(" ", "_"),
                    severity=mapped_severity,
                    issue_time=issue_time if not issue_time.tzinfo else issue_time.astimezone(timezone.utc).replace(tzinfo=None),
                    valid_from=issue_time if not issue_time.tzinfo else issue_time.astimezone(timezone.utc).replace(tzinfo=None),
                    valid_to=issue_time if not issue_time.tzinfo else issue_time.astimezone(timezone.utc).replace(tzinfo=None),
                    geographic_area=area_desc,
                    headline=headline,
                    description=description,
                    recommended_precautions=precautions,
                    is_verified=True,
                    is_synthetic=False,
                    data_type=DataType.OFFICIAL_WARNING,
                    polygon_coordinates=coords if coords else None,
                    affected_bounds=bounds,
                    storm_id=storm_id,
                )
            )

        return alerts
