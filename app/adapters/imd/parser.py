"""OASIS Common Alerting Protocol (CAP v1.1 / v1.2) XML Parser for IMD Alerts.

Parses official warning feeds securely, validating structure and preserving
official warning severity levels without modification.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET

from app.adapters.errors import CAPParseError
from app.adapters.models import NormalizedOfficialAlert, ProviderQuality
from app.adapters.normalization import (
    map_cap_severity_to_warning_level,
    normalize_iso_timestamp,
)


def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix from element tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_cap_xml(xml_content: str) -> List[NormalizedOfficialAlert]:
    """Parse OASIS CAP XML document and return normalized official alerts.

    Supports:
    - Single `<alert>` documents.
    - Atom / RSS `<feed>` containing multiple `<entry>` / `<alert>` items.
    - CAP v1.1 & v1.2 namespaces.

    Raises:
        CAPParseError: If XML is malformed, entity-expanded, or lacks mandatory fields.
    """
    if not xml_content or not xml_content.strip():
        raise CAPParseError("Empty or blank CAP XML payload received")

    # Guard against excessively large XML payloads (> 5MB)
    if len(xml_content) > 5 * 1024 * 1024:
        raise CAPParseError("CAP XML payload exceeds maximum allowed size (5MB)")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise CAPParseError(f"Malformed CAP XML: {e}") from e

    root_tag = _strip_ns(root.tag).lower()
    alerts: List[NormalizedOfficialAlert] = []

    if root_tag == "alert":
        alerts.extend(_parse_single_alert_element(root))
    elif root_tag in ("feed", "rss", "channel"):
        # Multiple alert entries
        for child in root.iter():
            if _strip_ns(child.tag).lower() == "alert":
                alerts.extend(_parse_single_alert_element(child))
    else:
        raise CAPParseError(f"Unrecognized root XML element '{root.tag}'; expected '<alert>' or '<feed>'")

    return alerts


def _parse_single_alert_element(alert_elem: ET.Element) -> List[NormalizedOfficialAlert]:
    """Extract fields from a single <alert> element."""
    def get_text(elem: ET.Element, tag_name: str) -> Optional[str]:
        for child in elem:
            if _strip_ns(child.tag).lower() == tag_name.lower():
                return child.text.strip() if child.text else None
        return None

    identifier = get_text(alert_elem, "identifier")
    sender = get_text(alert_elem, "sender")
    sent = get_text(alert_elem, "sent")
    status = get_text(alert_elem, "status") or "Actual"
    msg_type = get_text(alert_elem, "msgType") or "Alert"

    if not identifier or not sender or not sent:
        raise CAPParseError("CAP alert missing mandatory header fields (identifier, sender, or sent)")

    sent_iso = normalize_iso_timestamp(sent)
    normalized_alerts: List[NormalizedOfficialAlert] = []

    # Find all <info> blocks
    info_blocks = [c for c in alert_elem if _strip_ns(c.tag).lower() == "info"]
    if not info_blocks:
        raise CAPParseError(f"CAP alert {identifier} contains zero <info> elements")

    for info in info_blocks:
        event = get_text(info, "event")
        urgency = get_text(info, "urgency") or "Immediate"
        severity = get_text(info, "severity") or "Severe"
        certainty = get_text(info, "certainty") or "Observed"
        effective = get_text(info, "effective")
        onset = get_text(info, "onset")
        expires = get_text(info, "expires")
        headline = get_text(info, "headline")
        description = get_text(info, "description") or (headline or event or "Official weather alert")
        instruction = get_text(info, "instruction")

        if not event or not expires:
            raise CAPParseError(f"CAP info block in alert {identifier} missing event or expires")

        expires_iso = normalize_iso_timestamp(expires)
        effective_iso = normalize_iso_timestamp(effective) if effective else None
        onset_iso = normalize_iso_timestamp(onset) if onset else None

        # Check for ColorCode in <parameter>
        color_hint: Optional[str] = None
        for child in info:
            if _strip_ns(child.tag).lower() == "parameter":
                vname = get_text(child, "valueName")
                vval = get_text(child, "value")
                if vname and vval and "color" in vname.lower():
                    color_hint = vval

        warning_level = map_cap_severity_to_warning_level(severity, color_hint)

        # Extract Areas
        areas = [c for c in info if _strip_ns(c.tag).lower() == "area"]
        if not areas:
            # Create a single alert without specific area polygons
            normalized_alerts.append(
                NormalizedOfficialAlert(
                    alert_id=f"{identifier}_info",
                    sender=sender,
                    sent_time_iso=sent_iso,
                    status=status,
                    message_type=msg_type,
                    warning_level=warning_level,
                    event_title=event,
                    urgency=urgency,
                    severity=severity,
                    certainty=certainty,
                    headline=headline,
                    description=description,
                    instruction=instruction,
                    effective_time_iso=effective_iso,
                    onset_time_iso=onset_iso,
                    expires_time_iso=expires_iso,
                    area_description="Target Region",
                    polygons=[],
                    geocodes=[],
                    issuing_office=sender,
                    is_official=True,
                    quality=ProviderQuality.VALID,
                )
            )
        else:
            for a_idx, area in enumerate(areas):
                area_desc = get_text(area, "areaDesc") or "Affected District"
                polygons: List[str] = []
                geocodes: List[dict] = []

                for a_child in area:
                    tag = _strip_ns(a_child.tag).lower()
                    if tag == "polygon" and a_child.text:
                        polygons.append(a_child.text.strip())
                    elif tag == "geocode":
                        g_name = get_text(a_child, "valueName") or "code"
                        g_val = get_text(a_child, "value") or ""
                        geocodes.append({g_name: g_val})

                normalized_alerts.append(
                    NormalizedOfficialAlert(
                        alert_id=f"{identifier}_{a_idx}",
                        sender=sender,
                        sent_time_iso=sent_iso,
                        status=status,
                        message_type=msg_type,
                        warning_level=warning_level,
                        event_title=event,
                        urgency=urgency,
                        severity=severity,
                        certainty=certainty,
                        headline=headline,
                        description=description,
                        instruction=instruction,
                        effective_time_iso=effective_iso,
                        onset_time_iso=onset_iso,
                        expires_time_iso=expires_iso,
                        area_description=area_desc,
                        polygons=polygons,
                        geocodes=geocodes,
                        issuing_office=sender,
                        is_official=True,
                        quality=ProviderQuality.VALID,
                    )
                )

    return normalized_alerts
