"""Dedicated official warning and alert provider for OASIS/WMO CAP feeds."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
from typing import List, Optional, Dict, Any, Tuple

from app.brains.analyst_core.models.schemas import DataType, AlertSeverity, WarningFeedStatus
from app.brains.analyst_core.models.weather_data import OfficialAlert
from app.brains.analyst_core.models.retrieval import DataRetrievalResult, RetrievalStatus
from app.brains.analyst_core.data.cap_parser import CAPParser
from app.brains.analyst_core.data.cache import TTLCache


class OfficialWarningProvider(ABC):
    """Abstract interface for official hydrometeorological alerting feeds."""

    @abstractmethod
    def get_active_warnings(
        self,
        location: str,
        current_time: Optional[datetime] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[OfficialAlert]:
        """Retrieves currently active official alerts for the given location."""
        pass


class CAPAlertProvider(OfficialWarningProvider):
    """Production provider for OASIS / WMO Common Alerting Protocol feeds (IMD, NDMA, WMO Alert Hub)."""

    def __init__(
        self,
        cap_parser: Optional[CAPParser] = None,
        cache: Optional[TTLCache] = None,
        session: Optional[Any] = None,
        feed_sources: Optional[Dict[str, Any]] = None,
        is_feed_available: bool = True,
    ):
        self.cap_parser = cap_parser or CAPParser()
        self.cache = cache or TTLCache(default_ttl_seconds=300)
        self.session = session
        self.feed_sources = feed_sources if feed_sources is not None else {}
        self.is_feed_available = is_feed_available

    def get_warnings_with_status(
        self,
        location: str,
        current_time: Optional[datetime] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Tuple[List[OfficialAlert], WarningFeedStatus, DataRetrievalResult]:
        """Differentiates SOURCE_UNAVAILABLE from genuinely NO_WARNING_ISSUED."""
        now = current_time or datetime.utcnow()
        loc_key = location.strip().lower()

        if not self.is_feed_available:
            res = DataRetrievalResult(
                status=RetrievalStatus.SOURCE_UNAVAILABLE,
                provider_name="IMD/WMO CAP Feed Service",
                error_message="CAP warning feed is unreachable or offline.",
                data_type=DataType.OFFICIAL_WARNING,
            )
            return [], WarningFeedStatus.SOURCE_UNAVAILABLE, res

        try:
            alerts = self.get_active_warnings(location, current_time=now, latitude=latitude, longitude=longitude)
            payload_bytes = json.dumps([a.dict() for a in alerts], default=str).encode("utf-8")
            digest = hashlib.sha256(payload_bytes).hexdigest()

            if alerts:
                res = DataRetrievalResult(
                    status=RetrievalStatus.SUCCESS,
                    provider_name="IMD/WMO CAP Feed Service",
                    records_count=len(alerts),
                    data_type=DataType.OFFICIAL_WARNING,
                    payload_sha256=digest,
                )
                return alerts, WarningFeedStatus.ACTIVE_WARNINGS_FOUND, res
            else:
                res = DataRetrievalResult(
                    status=RetrievalStatus.EMPTY_RESULT,
                    provider_name="IMD/WMO CAP Feed Service",
                    records_count=0,
                    data_type=DataType.OFFICIAL_WARNING,
                    payload_sha256=digest,
                )
                return [], WarningFeedStatus.NO_WARNING_ISSUED, res
        except Exception as e:
            res = DataRetrievalResult(
                status=RetrievalStatus.ERROR,
                provider_name="IMD/WMO CAP Feed Service",
                error_message=str(e),
                data_type=DataType.OFFICIAL_WARNING,
            )
            return [], WarningFeedStatus.SOURCE_UNAVAILABLE, res

    def get_active_warnings(
        self,
        location: str,
        current_time: Optional[datetime] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[OfficialAlert]:
        """Fetches, parses, deduplicates, and filters active warnings for location."""
        now = current_time or datetime.utcnow()
        loc_key = location.strip().lower()
        cache_key = f"cap_active:{loc_key}:{now.strftime('%Y%m%d%H%M')}"
        cached = self.cache.get(cache_key)
        if cached:
            return [OfficialAlert(**c) for c in cached]

        all_alerts: List[OfficialAlert] = []

        # Ingest from configured feeds or mock responses
        for key, raw_feed in self.feed_sources.items():
            if isinstance(raw_feed, str) and "<alert" in raw_feed:
                parsed = self.cap_parser.parse_cap_xml(raw_feed)
                all_alerts.extend(parsed)
            elif isinstance(raw_feed, dict):
                parsed = self.cap_parser.parse_cap_json(raw_feed)
                all_alerts.extend(parsed)
            elif isinstance(raw_feed, list):
                for item in raw_feed:
                    if isinstance(item, OfficialAlert):
                        all_alerts.append(item)
                    elif isinstance(item, dict):
                        all_alerts.append(OfficialAlert(**item))

        # Filter by location relevance and temporal validity
        filtered: List[OfficialAlert] = []
        seen_ids = set()

        for alert in all_alerts:
            if alert.alert_id in seen_ids:
                continue

            # 1. Strict Temporal Validity: valid_from <= now <= valid_to
            is_time_valid = alert.valid_from <= now <= alert.valid_to
            if not is_time_valid:
                continue

            # 2. Spatial match: polygon/coordinates or geographic area
            is_spatial_match = alert.matches_location(location, latitude=latitude, longitude=longitude) or (
                loc_key in alert.headline.lower() or loc_key in alert.description.lower()
            )
            if is_spatial_match:
                seen_ids.add(alert.alert_id)
                filtered.append(alert)

        self.cache.set(cache_key, [a.dict() for a in filtered])
        return filtered
