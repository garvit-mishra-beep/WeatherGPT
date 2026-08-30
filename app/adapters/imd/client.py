"""IMD Official Warning & CAP Alert Ingestion Client."""

import logging
from typing import List, Optional
import httpx

from app.adapters.base import BaseWarningProvider
from app.adapters.errors import (
    CAPParseError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.adapters.imd.parser import parse_cap_xml
from app.adapters.models import NormalizedOfficialAlert, ProviderAuthority
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class IMDWarningProvider(BaseWarningProvider):
    """Authoritative IMD / NDMA Common Alerting Protocol (CAP) client."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client

    @property
    def name(self) -> str:
        return "imd_cap"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.OFFICIAL

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.imd_timeout_seconds),
                headers={
                    "User-Agent": "WeatherGPT-Meteorological-Adapter/1.0",
                    "Accept": "application/xml, text/xml, application/rss+xml",
                },
            )
        return self._http_client

    async def get_active_warnings(
        self,
        district_name: Optional[str] = None,
        state_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[NormalizedOfficialAlert]:
        """Fetch and return active official warnings from IMD / NDMA Sachet feed."""
        url = self.settings.imd_cap_url
        client = await self._get_client()

        try:
            headers = {}
            if self.settings.imd_api_key:
                headers["Authorization"] = f"Bearer {self.settings.imd_api_key}"

            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ProviderResponseError(
                    f"IMD CAP feed returned status {response.status_code}",
                    provider=self.name,
                    details={"status_code": response.status_code, "url": url},
                )

            raw_xml = response.text
            all_alerts = parse_cap_xml(raw_xml)

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                f"Timeout connecting to IMD CAP endpoint ({self.settings.imd_timeout_seconds}s): {e}",
                provider=self.name,
            ) from e
        except (httpx.NetworkError, httpx.ConnectError) as e:
            raise ProviderUnavailableError(
                f"Unable to connect to IMD CAP endpoint: {e}",
                provider=self.name,
            ) from e
        except (CAPParseError, ProviderResponseError):
            raise
        except Exception as e:
            raise ProviderUnavailableError(
                f"Unexpected error fetching IMD CAP warnings: {e}",
                provider=self.name,
            ) from e

        # Filter by district/state if specified
        if district_name:
            norm_dist = district_name.strip().lower()
            filtered = [
                a for a in all_alerts
                if norm_dist in a.area_description.lower() or norm_dist in a.description.lower()
            ]
            return filtered

        if state_name:
            norm_state = state_name.strip().lower()
            filtered = [
                a for a in all_alerts
                if norm_state in a.area_description.lower() or norm_state in a.description.lower()
            ]
            return filtered

        return all_alerts

    async def check_health(self) -> bool:
        """Check if IMD CAP endpoint is reachable."""
        try:
            client = await self._get_client()
            resp = await client.head(self.settings.imd_cap_url)
            return resp.status_code < 500
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
