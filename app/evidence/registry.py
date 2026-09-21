"""Canonical Source Registry for VAYUBODHAK Phase 2A.

Maintains governance, source metadata, authority tiering (E0–E5), and
operational boundaries across meteorological, hydrological, and satellite sources.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.evidence.models import (
    EvidenceClass,
    FreshnessPolicy,
    SourceAuthorityLevel,
    SourceMetadata,
)


class SourceRegistry:
    """Thread-safe catalog and governance registry for all ingestible sources."""

    def __init__(self) -> None:
        self._sources: Dict[str, SourceMetadata] = {}
        self._initialize_canonical_sources()

    def _initialize_canonical_sources(self) -> None:
        """Pre-registers authoritative sources defined by the VAYUBODHAK research."""
        canonical_sources: List[SourceMetadata] = [
            # 1. IMD - India Meteorological Department (E0 Operational Authority)
            SourceMetadata(
                source_id="IMD",
                source_name="India Meteorological Department",
                authority="Ministry of Earth Sciences (MoES), Government of India",
                source_type="OFFICIAL_WARNING_AND_OBSERVATION",
                authority_level=SourceAuthorityLevel.E0,
                product_id="IMD_CAP_AND_SURFACE_OBS",
                version="1.0",
                is_active=True,
                base_url="https://mausam.imd.gov.in",
                description="Primary statutory national authority for official weather forecasts, severe weather warnings, and cyclone advisories in India.",
                supported_classes=[
                    EvidenceClass.OFFICIAL_WARNING,
                    EvidenceClass.OBSERVATION,
                    EvidenceClass.FORECAST,
                    EvidenceClass.NOWCAST,
                ],
                license_notes="Government Open Data License - India (GODL)",
                provenance_requirements="Preserve official bulletin timestamp, severity level, headline, and issuing meteorological centre.",
                freshness_policies={
                    "OFFICIAL_WARNING": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=True,
                        description="Strictly governed by official validity window (valid_to). Never marked stale while valid.",
                    ),
                    "NOWCAST": FreshnessPolicy(
                        max_age_seconds=7200,
                        enforce_validity_window=True,
                        description="IMD Doppler radar nowcasts expire after 2 hours due to rapid storm evolution.",
                    ),
                    "OBSERVATION": FreshnessPolicy(
                        max_age_seconds=10800,  # 3 hours
                        enforce_validity_window=True,
                        description="Standard 3-hour synoptic surface observation cycle.",
                    ),
                    "FORECAST": FreshnessPolicy(
                        max_age_seconds=86400,
                        enforce_validity_window=True,
                        description="Official district forecast bulletins valid up to 24h from issue.",
                    ),
                },
            ),
            # 2. CWC - Central Water Commission (E0 Operational Flood/Hydrology Authority)
            SourceMetadata(
                source_id="CWC",
                source_name="Central Water Commission",
                authority="Ministry of Jal Shakti, Government of India",
                source_type="HYDROLOGICAL_OBSERVATION_AND_FORECAST",
                authority_level=SourceAuthorityLevel.E0,
                product_id="CWC_FLOOD_FORECAST",
                version="1.0",
                is_active=True,
                base_url="http://ffs.tamcwc.gov.in",
                description="Statutory authority for river basin monitoring, reservoir levels, and official riverine flood forecasts. Must NOT be interpolated nationwide.",
                supported_classes=[
                    EvidenceClass.OFFICIAL_WARNING,
                    EvidenceClass.OBSERVATION,
                    EvidenceClass.FORECAST,
                ],
                license_notes="Government Open Data License - India (GODL)",
                provenance_requirements="Requires exact station/basin identifier; no spatial extrapolation to unmonitored catchments.",
                freshness_policies={
                    "OFFICIAL_WARNING": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=True,
                        description="Hydrological flood alerts governed by valid_to expiration.",
                    ),
                    "OBSERVATION": FreshnessPolicy(
                        max_age_seconds=21600,  # 6 hours
                        enforce_validity_window=True,
                        description="River gauge station observation cycle.",
                    ),
                },
            ),
            # 3. NDMA_SACHET - National Disaster Management Authority (E0 Dissemination)
            SourceMetadata(
                source_id="NDMA_SACHET",
                source_name="NDMA SACHET Early Warning Portal",
                authority="National Disaster Management Authority, Government of India",
                source_type="OFFICIAL_CAP_DISSEMINATION",
                authority_level=SourceAuthorityLevel.E0,
                product_id="SACHET_CAP_FEED",
                version="2.0",
                is_active=True,
                base_url="https://sachet.ndma.gov.in",
                description="National disaster alert dissemination platform aggregating CAP feeds across central and state authorities.",
                supported_classes=[EvidenceClass.OFFICIAL_WARNING],
                license_notes="Government Official Emergency Bulletin",
                provenance_requirements="Preserve CAP identifier, effective time, expires time, and target polygon.",
                freshness_policies={
                    "OFFICIAL_WARNING": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=True,
                        description="CAP emergency alerts strictly governed by valid_to.",
                    ),
                },
            ),
            # 4. GSI - Geological Survey of India (E2 Scientific Landslide Authority)
            SourceMetadata(
                source_id="GSI",
                source_name="Geological Survey of India",
                authority="Ministry of Mines, Government of India",
                source_type="SPATIAL_LANDSLIDE_SUSCEPTIBILITY",
                authority_level=SourceAuthorityLevel.E2,
                product_id="GSI_NLSM_SUSCEPTIBILITY",
                version="NLSM-v1",
                is_active=True,
                base_url="https://bhukosh.gsi.gov.in",
                description="National Landslide Susceptibility Mapping baseline datasets. Provides geological context; does NOT supply universal rainfall triggering thresholds.",
                supported_classes=[EvidenceClass.SPATIAL_STATIC],
                license_notes="Academic and Research Access / GSI Data Policy",
                provenance_requirements="Must specify NLSM polygon/grid ID and slope susceptibility class.",
                freshness_policies={
                    "SPATIAL_STATIC": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=False,
                        description="Geological landslide susceptibility baselines are static multi-year reference datasets.",
                    ),
                },
            ),
            # 5. NASA_IMERG - NASA GPM Satellite Precipitation (E2 Government / Scientific Dataset)
            SourceMetadata(
                source_id="NASA_IMERG",
                source_name="NASA Integrated Multi-satellitE Retrievals for GPM",
                authority="NASA Goddard Space Flight Center / JAXA",
                source_type="SATELLITE_PRECIPITATION_ESTIMATE",
                authority_level=SourceAuthorityLevel.E2,
                product_id="IMERG_FINAL_0P1DEG",
                version="V07B",
                is_active=True,
                base_url="https://gpm.nasa.gov/data/imerg",
                description="Global satellite-gauge precipitation product (0.1 deg) produced by NASA GSFC and JAXA. Assigned E2 (Government / Scientific Dataset). Supporting spatial evidence only; must NOT be represented as direct in-situ rain gauge truth or an official Indian warning authority.",
                supported_classes=[EvidenceClass.OBSERVATION, EvidenceClass.DERIVED],
                license_notes="NASA Open Data Policy (Free and open)",
                provenance_requirements="Record satellite calibration run (Early/Late/Final) and grid cell coordinates.",
                freshness_policies={
                    "OBSERVATION": FreshnessPolicy(
                        max_age_seconds=86400,  # 24 hours
                        enforce_validity_window=True,
                        description="IMERG daily/sub-daily calibrated precipitation retrievals.",
                    ),
                },
            ),
            # 6. OPEN_METEO - Aggregated Meteorological API (E2 Scientific Dataset API)
            SourceMetadata(
                source_id="OPEN_METEO",
                source_name="Open-Meteo Weather API",
                authority="Open-Meteo GmbH / Open Data Aggregation",
                source_type="NWP_AND_REANALYSIS_API",
                authority_level=SourceAuthorityLevel.E2,
                product_id="OPEN_METEO_FORECAST",
                version="1.0",
                is_active=True,
                base_url="https://api.open-meteo.com",
                description="Aggregated surface weather and NWP point forecasts from global meteorological services (DWD, NOAA, ECMWF).",
                supported_classes=[EvidenceClass.OBSERVATION, EvidenceClass.FORECAST],
                license_notes="Creative Commons Attribution 4.0 International (CC BY 4.0)",
                provenance_requirements="Preserve query latitude/longitude, generationtime_ms, and attribution.",
                freshness_policies={
                    "OBSERVATION": FreshnessPolicy(
                        max_age_seconds=21600,  # 6 hours
                        enforce_validity_window=True,
                        description="Surface hourly weather observations.",
                    ),
                    "FORECAST": FreshnessPolicy(
                        max_age_seconds=86400,
                        enforce_validity_window=True,
                        description="Aggregated point forecasts valid up to 24h.",
                    ),
                },
            ),
            # 7. NWP_GFS - NOAA Global Forecast System (E2 Scientific NWP Model)
            SourceMetadata(
                source_id="NWP_GFS",
                source_name="Global Forecast System (GFS)",
                authority="National Oceanic and Atmospheric Administration (NOAA) / NCEP",
                source_type="NUMERICAL_WEATHER_PREDICTION",
                authority_level=SourceAuthorityLevel.E2,
                product_id="GFS_0P25_GRID",
                version="v16",
                is_active=True,
                base_url="https://nomads.ncep.noaa.gov",
                description="Global operational NWP model run 4 times daily by US NOAA/NCEP. Must remain explicitly distinguished from ground observations and official alerts.",
                supported_classes=[EvidenceClass.FORECAST],
                license_notes="US Government Open Data (Public Domain)",
                provenance_requirements="Preserve model initialization time (cycle 00z/06z/12z/18z) and forecast hour offset (f000..f384).",
                freshness_policies={
                    "FORECAST": FreshnessPolicy(
                        max_age_seconds=86400,
                        enforce_validity_window=True,
                        description="GFS cycle runs valid through forecast lead horizon.",
                    ),
                },
            ),
            # 8. NWP_ECMWF - European Centre for Medium-Range Weather Forecasts (E1 International Authority)
            SourceMetadata(
                source_id="NWP_ECMWF",
                source_name="European Centre for Medium-Range Weather Forecasts",
                authority="ECMWF",
                source_type="NUMERICAL_WEATHER_PREDICTION",
                authority_level=SourceAuthorityLevel.E1,
                product_id="IFS_HRES_AIFS",
                version="CY48R1",
                is_active=True,
                base_url="https://www.ecmwf.int",
                description="Independent intergovernmental organisation supported by 35 member states. Assigned E1 (International Authority). OPERATIONAL BOUNDARY IN INDIA: Serves exclusively as secondary global medium-range numerical prediction guidance (EvidenceClass.FORECAST); it has NO statutory authority to issue official weather warnings, flood alerts, or disaster advisories in India, which are reserved exclusively for statutory E0 authorities (IMD, CWC, NDMA).",
                supported_classes=[EvidenceClass.FORECAST],
                license_notes="ECMWF Open Data Licence",
                provenance_requirements="Preserve initialization cycle and step hours.",
                freshness_policies={
                    "FORECAST": FreshnessPolicy(
                        max_age_seconds=86400,
                        enforce_validity_window=True,
                        description="ECMWF IFS runs remain valid up to their step horizon or 24 hours from initialization.",
                    ),
                },
            ),
            # 9. WMO - World Meteorological Organization (E1 International Standard)
            SourceMetadata(
                source_id="WMO",
                source_name="World Meteorological Organization",
                authority="United Nations",
                source_type="INTERNATIONAL_STANDARDS_AGENCY",
                authority_level=SourceAuthorityLevel.E1,
                product_id="WMO_MET_STANDARDS",
                version="WMO-No. 49",
                is_active=True,
                base_url="https://wmo.int",
                description="International standardizing body for meteorological observation practices and climate normal baselines (1991-2020).",
                supported_classes=[EvidenceClass.SPATIAL_STATIC, EvidenceClass.GROUND_TRUTH],
                license_notes="UN Open Access",
                provenance_requirements="Reference standard guideline publication.",
                freshness_policies={
                    "SPATIAL_STATIC": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=False,
                        description="WMO standard specifications and climatological normal baselines are multi-decadal references.",
                    ),
                    "GROUND_TRUTH": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=False,
                        description="Climatological ground truth normals do not decay hourly.",
                    ),
                },
            ),
            # 10. UNDRR - UN Disaster Risk Reduction (E1 International Standard)
            SourceMetadata(
                source_id="UNDRR",
                source_name="UN Office for Disaster Risk Reduction",
                authority="United Nations",
                source_type="INTERNATIONAL_FRAMEWORK",
                authority_level=SourceAuthorityLevel.E1,
                product_id="SENDAI_FRAMEWORK_METRICS",
                version="Sendai 2015-2030",
                is_active=True,
                base_url="https://www.undrr.org",
                description="Global standards for disaster risk assessment, hazard taxonomy, and vulnerability indices.",
                supported_classes=[EvidenceClass.SPATIAL_STATIC],
                license_notes="UN Open Publications",
                provenance_requirements="Reference Sendai Framework indicator classification.",
                freshness_policies={
                    "SPATIAL_STATIC": FreshnessPolicy(
                        max_age_seconds=None,
                        enforce_validity_window=False,
                        description="Sendai Framework metrics and disaster taxonomy are persistent decadal standards.",
                    ),
                },
            ),
        ]

        for s in canonical_sources:
            self._sources[s.source_id] = s

    def register_source(self, metadata: SourceMetadata) -> SourceMetadata:
        """Registers or updates a source in the registry.
        
        Enforces governance:
        - Non-statutory sources cannot claim E0 operational authority.
        - Non-statutory sources cannot register EvidenceClass.OFFICIAL_WARNING.
        """
        if (
            metadata.authority_level == SourceAuthorityLevel.E0
            and metadata.source_id not in ("IMD", "CWC", "NDMA_SACHET")
        ):
            raise ValueError(
                f"Source '{metadata.source_id}' cannot be registered with E0 Operational Authority. "
                "E0 tier is reserved exclusively for statutory Indian operational authorities (IMD, CWC, NDMA)."
            )
        if (
            EvidenceClass.OFFICIAL_WARNING in metadata.supported_classes
            and metadata.source_id not in ("IMD", "CWC", "NDMA_SACHET")
        ):
            raise ValueError(
                f"Source '{metadata.source_id}' cannot register EvidenceClass.OFFICIAL_WARNING. "
                "Official warning dissemination for India is reserved exclusively for statutory authorities (IMD, CWC, NDMA)."
            )
        self._sources[metadata.source_id] = metadata
        return metadata

    def get_source(self, source_id: str) -> Optional[SourceMetadata]:
        """Retrieves metadata for a registered source."""
        return self._sources.get(source_id)

    def list_sources(self, active_only: bool = True) -> List[SourceMetadata]:
        """Lists all registered sources."""
        if active_only:
            return [s for s in self._sources.values() if s.is_active]
        return list(self._sources.values())

    def validate_source_class(self, source_id: str, evidence_class: EvidenceClass) -> bool:
        """Validates whether a source is authorized to produce the specified EvidenceClass."""
        source = self.get_source(source_id)
        if not source or not source.is_active:
            return False
        return evidence_class in source.supported_classes

    def record_success(self, source_id: str, timestamp: Optional[datetime] = None) -> None:
        """Records a successful operational data ingestion."""
        source = self.get_source(source_id)
        if source:
            source.last_success = timestamp or datetime.now(timezone.utc)
            source.consecutive_failures = 0
            source.health_status = "ONLINE"

    def record_failure(self, source_id: str, timestamp: Optional[datetime] = None, error_msg: Optional[str] = None) -> None:
        """Records a failed operational data ingestion."""
        source = self.get_source(source_id)
        if source:
            source.last_failure = timestamp or datetime.now(timezone.utc)
            source.consecutive_failures += 1
            if source.consecutive_failures >= 5:
                source.health_status = "FAILED"
            else:
                source.health_status = "DEGRADED"

    def set_source_active(self, source_id: str, is_active: bool) -> SourceMetadata:
        """Enables or disables an operational data source."""
        source = self.get_source(source_id)
        if not source:
            raise KeyError(f"Source '{source_id}' not found in SourceRegistry")
        source.is_active = is_active
        if not is_active:
            source.health_status = "DISABLED"
        elif source.consecutive_failures == 0:
            source.health_status = "ONLINE"
        return source

    def get_health_summary(self) -> Dict[str, Any]:
        """Provides operational health telemetry summary across all registered sources."""
        summary = {}
        for s_id, s in self._sources.items():
            summary[s_id] = {
                "source_name": s.source_name,
                "authority_level": s.authority_level.value,
                "is_active": s.is_active,
                "health_status": s.health_status,
                "consecutive_failures": s.consecutive_failures,
                "last_success_iso": s.last_success.isoformat() if s.last_success else None,
                "last_failure_iso": s.last_failure.isoformat() if s.last_failure else None,
                "coverage": s.coverage,
                "update_frequency": s.update_frequency,
            }
        return summary


# Singleton instance for system-wide access
source_registry = SourceRegistry()
