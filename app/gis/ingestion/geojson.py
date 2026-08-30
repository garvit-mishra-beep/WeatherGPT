"""GeoJSON Administrative Boundary Ingestion Engine & CLI.

Supports idempotent upserting of Country, State, District, and Sub-District
boundaries from GeoJSON FeatureCollections into PostgreSQL + PostGIS.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import create_async_engine_from_settings, create_session_factory, dispose_engine
from app.gis.ingestion.validators import (
    GeoJSONValidationError,
    extract_centroid_and_bbox,
    normalize_and_validate_geometry,
    validate_boundary_properties,
    validate_feature_collection,
)
from app.gis.repositories.boundaries import (
    CountryRepository,
    DistrictRepository,
    StateRepository,
    SubDistrictRepository,
)
from app.gis.schemas.boundaries import AdminLevel, IngestionSummary

logger = logging.getLogger(__name__)


class GeoJSONBoundaryIngester:
    """Idempotent ingestion processor for administrative boundary GeoJSON datasets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.countries = CountryRepository(session)
        self.states = StateRepository(session)
        self.districts = DistrictRepository(session)
        self.subdistricts = SubDistrictRepository(session)

    async def ingest_geojson(
        self,
        data: Union[Dict[str, Any], str, Path],
        level: AdminLevel,
    ) -> IngestionSummary:
        """Ingest GeoJSON data for the specified administrative level.

        Args:
            data: A loaded dict, a JSON string, or a Path to a GeoJSON file.
            level: The target administrative level.

        Returns:
            IngestionSummary: Counts of inserted, updated, and failed features.
        """
        raw_dict = self._load_data_dict(data)
        features = validate_feature_collection(raw_dict)

        summary = IngestionSummary(level=level, total_features=len(features))

        for idx, feat in enumerate(features):
            try:
                await self._process_feature(feat, level)
                summary.inserted += 1  # Note: upsert in postgres handles insert/update
            except Exception as exc:
                summary.failed += 1
                err_msg = f"Feature {idx} failed: {exc}"
                logger.warning(err_msg)
                summary.errors.append(err_msg)

        await self.session.commit()
        logger.info(
            "Ingestion completed for level=%s: total=%d, succeeded=%d, failed=%d",
            level.value,
            summary.total_features,
            summary.inserted,
            summary.failed,
        )
        return summary

    async def _process_feature(self, feat: Dict[str, Any], level: AdminLevel) -> None:
        props = feat.get("properties") or {}
        geom_raw = feat.get("geometry")

        if not geom_raw:
            raise GeoJSONValidationError("Feature is missing geometry")

        # 1. Validate & normalize properties
        cleaned_props = validate_boundary_properties(props, level)

        # 2. Validate & normalize geometry to MultiPolygon EPSG:4326
        cleaned_geom = normalize_and_validate_geometry(geom_raw)
        cleaned_props["geom"] = cleaned_geom

        # 3. Derive centroid if not already present
        if cleaned_props.get("centroid_lat") is None or cleaned_props.get("centroid_lon") is None:
            c_lat, c_lon = extract_centroid_and_bbox(cleaned_geom["coordinates"])
            cleaned_props["centroid_lat"] = c_lat
            cleaned_props["centroid_lon"] = c_lon

        # 4. Delegate to the corresponding repository for idempotent upsert
        if level == AdminLevel.COUNTRY:
            await self.countries.upsert(cleaned_props)
        elif level == AdminLevel.STATE:
            await self.states.upsert(cleaned_props)
        elif level == AdminLevel.DISTRICT:
            await self.districts.upsert(cleaned_props)
        elif level == AdminLevel.SUBDISTRICT:
            await self.subdistricts.upsert(cleaned_props)

    def _load_data_dict(self, data: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
        if isinstance(data, dict):
            return data
        if isinstance(data, Path) or (isinstance(data, str) and not data.strip().startswith("{")):
            path = Path(data)
            if not path.exists():
                raise FileNotFoundError(f"GeoJSON file not found at: {path}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        if isinstance(data, str):
            return json.loads(data)
        raise ValueError(f"Unsupported data source type: {type(data)}")


async def run_ingestion_cli(file_path: Path, level_str: str) -> IngestionSummary:
    """CLI helper to execute ingestion from a standalone script."""
    level = AdminLevel(level_str.lower())
    engine = create_async_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            ingester = GeoJSONBoundaryIngester(session)
            return await ingester.ingest_geojson(file_path, level)
    finally:
        await dispose_engine(engine)


def main() -> None:
    parser = argparse.ArgumentParser(description="WeatherGPT GeoJSON Administrative Boundary Ingestion Tool")
    parser.add_argument("--file", "-f", required=True, type=Path, help="Path to input GeoJSON file")
    parser.add_argument(
        "--level",
        "-l",
        required=True,
        choices=["country", "state", "district", "subdistrict"],
        help="Administrative level to ingest",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    summary = asyncio.run(run_ingestion_cli(args.file, args.level))
    print(
        f"Ingestion result: Total={summary.total_features}, "
        f"Succeeded={summary.inserted}, Failed={summary.failed}"
    )


if __name__ == "__main__":
    main()
