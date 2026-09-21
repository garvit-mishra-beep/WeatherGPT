"""Exposure Method Registry for VAYUBODHAK Phase 4.

Provides governed, versioned, transparent exposure quantification methodologies.
Enforces ACTIVE/DRAFT/RETIRED lifecycle. Only ACTIVE methods execute.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.exposure.models import ExposureMethodStatus, ExposureType, SpatialResolution


class ExposureMethod(BaseModel):
    """Governed exposure quantification methodology specification."""
    method_id: str = Field(..., description="Unique method code (e.g. 'EXP-METH-POP-ADMIN-001')")
    method_name: str = Field(..., description="Human-readable method title")
    method_version: str = Field(default="1.0.0", description="SemVer version")
    exposure_type: ExposureType = Field(..., description="Target exposure domain")
    input_dataset_type: str = Field(..., description="Type of input data expected")
    spatial_method: str = Field(..., description="Spatial operation (e.g. Area-weighted intersection, Point containment)")
    calculation_logic: str = Field(..., description="Mathematical or algorithmic formula")
    assumptions: List[str] = Field(default_factory=list, description="Methodological assumptions")
    limitations: List[str] = Field(default_factory=list, description="Known analytical limitations")
    spatial_resolution: SpatialResolution = Field(..., description="Granularity")
    temporal_basis: str = Field(..., description="Temporal nature (e.g. Decennial census baseline, Static GIS)")
    quality_handling: str = Field(..., description="How data gaps or quality flags are processed")
    uncertainty_description: str = Field(..., description="Characterization of output uncertainty")
    measures: str = Field(..., description="Explicit definition of what the method measures")
    does_not_measure: str = Field(..., description="Explicit negative boundaries: what it does NOT measure")
    status: ExposureMethodStatus = Field(default=ExposureMethodStatus.ACTIVE)
    test_coverage: str = Field(default="tests/test_exposure_modeling.py")


class ExposureMethodRegistry:
    """Registry governing all active, draft, and retired exposure methods."""

    def __init__(self) -> None:
        self._methods: Dict[str, ExposureMethod] = {}
        self._register_canonical_methods()

    def register_method(self, method: ExposureMethod, allow_overwrite: bool = False) -> None:
        """Registers a method. Once registered, active methods cannot be mutated without version bump."""
        if method.method_id in self._methods and not allow_overwrite:
            existing = self._methods[method.method_id]
            if existing.status == ExposureMethodStatus.RETIRED:
                raise ValueError(f"Cannot overwrite RETIRED method {method.method_id}")
            if existing.method_version == method.method_version:
                raise ValueError(
                    f"Method {method.method_id} version {method.method_version} already registered. "
                    f"Bump version to register updates."
                )
        self._methods[method.method_id] = method

    def get_method(self, method_id: str) -> Optional[ExposureMethod]:
        """Retrieves a method by ID."""
        return self._methods.get(method_id)

    def get_active_method(self, method_id: str) -> ExposureMethod:
        """Retrieves an ACTIVE method, raising ValueError if not found, draft, or retired."""
        method = self._methods.get(method_id)
        if not method:
            raise ValueError(f"Exposure method {method_id} not found in registry")
        if method.status != ExposureMethodStatus.ACTIVE:
            raise ValueError(
                f"Exposure method {method_id} cannot be executed; status is {method.status.value}"
            )
        return method

    def list_methods(
        self,
        exposure_type: Optional[ExposureType] = None,
        status: Optional[ExposureMethodStatus] = None,
    ) -> List[ExposureMethod]:
        """Lists methods matching optional exposure_type and status filters."""
        results = list(self._methods.values())
        if exposure_type:
            results = [m for m in results if m.exposure_type == exposure_type]
        if status:
            results = [m for m in results if m.status == status]
        return results

    def retire_method(self, method_id: str) -> None:
        """Transitions a method to RETIRED status."""
        method = self._methods.get(method_id)
        if not method:
            raise ValueError(f"Method {method_id} not found")
        method.status = ExposureMethodStatus.RETIRED

    def _register_canonical_methods(self) -> None:
        """Registers the 7 canonical VAYUBODHAK Phase 4 exposure methods."""

        # 1. Area-Weighted Administrative Population
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-POP-ADMIN-001",
                method_name="Area-Weighted Administrative Population Estimation",
                method_version="1.0.0",
                exposure_type=ExposureType.POPULATION_ADMIN,
                input_dataset_type="Administrative Boundary + Census Population Record",
                spatial_method="Geodesic Polygon Intersection + Area Proportionality",
                calculation_logic=(
                    "Exposed_Pop = Admin_Population * (Exposed_Area_sqkm / Total_Admin_Area_sqkm)"
                ),
                assumptions=[
                    "Population is uniformly distributed across the administrative unit.",
                    "Administrative boundary alignment between hazard polygon and census polygon is consistent.",
                ],
                limitations=[
                    "Uniform distribution assumption does not reflect urban/rural clustering within districts.",
                    "Based on decennial census figures (historical baseline), not real-time population.",
                    "May overestimate exposure in uninhabited mountainous/forest portions of districts.",
                ],
                spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
                temporal_basis="Decennial Census Baseline (2011)",
                quality_handling="Returns 0.0 with MISSING quality state if census record is absent.",
                uncertainty_description="High variance in non-homogeneous rural/urban districts; labeled as area-weighted estimate.",
                measures="Estimated number of residents whose administrative unit overlaps the hazard footprint.",
                does_not_measure="Real-time headcounts, evacuation status, casualties, injuries, or demographic vulnerability.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 2. Gridded Population Surface
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-POP-GRID-001",
                method_name="Gridded Population Surface Zonal Summation",
                method_version="1.0.0",
                exposure_type=ExposureType.POPULATION_GRIDDED,
                input_dataset_type="Raster/Mesh Gridded Population Surface (e.g. WorldPop 1km)",
                spatial_method="Zonal Intersection with Grid Cell Polygons",
                calculation_logic="Exposed_Pop = Sum(Cell_Population * Cell_Overlap_Fraction)",
                assumptions=[
                    "Dasymetrically modeled gridded population accurately captures settlement density.",
                    "Cell boundaries accurately align with hazard footprint coordinates.",
                ],
                limitations=[
                    "Resolution limited by grid cell dimensions (e.g. 1km²).",
                    "Dasymetric modeling introduces algorithm-specific smoothing.",
                ],
                spatial_resolution=SpatialResolution.POPULATION_GRID_CELL,
                temporal_basis="Model-projected raster surface",
                quality_handling="Missing cells treated as unpopulated or missing; never fabricated.",
                uncertainty_description="Moderate resolution uncertainty based on raster cell size.",
                measures="Estimated count of residents located in raster cells intersecting the hazard footprint.",
                does_not_measure="Real-time mobility, daytime vs nighttime shifts, or casualties.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 3. Critical Point Asset Containment
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-ASSET-POINT-001",
                method_name="Critical Point Asset Spatial Containment",
                method_version="1.0.0",
                exposure_type=ExposureType.CRITICAL_INFRASTRUCTURE,
                input_dataset_type="Point Asset Geometries (Hospitals, Schools, Emergency Services)",
                spatial_method="Point-in-Polygon Geodesic Containment (ST_Contains / Ray-Casting)",
                calculation_logic="Exposed_Assets = [Asset for Asset in Assets if Hazard_Polygon.contains(Asset.point)]",
                assumptions=[
                    "Point coordinates accurately represent asset physical facility location.",
                ],
                limitations=[
                    "Point representation does not capture large institutional campus boundaries.",
                    "Does not account for auxiliary infrastructure (e.g. access roads, power lines).",
                ],
                spatial_resolution=SpatialResolution.POINT,
                temporal_basis="Static infrastructure registry",
                quality_handling="Invalid coordinates flagged as INVALID quality state.",
                uncertainty_description="Low geometric uncertainty for verified GPS coordinates.",
                measures="Identified physical facilities whose location point falls within the hazard boundary.",
                does_not_measure="Operational status, structural damage, capacity loss, or service interruption.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 4. Linear Transport Infrastructure Length
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-INFRA-ROAD-001",
                method_name="Linear Transport Infrastructure Metric Length Intersection",
                method_version="1.0.0",
                exposure_type=ExposureType.ROAD,
                input_dataset_type="LineString / MultiLineString Road Segments",
                spatial_method="Line-Polygon Intersection & Metric Geodesic Length Summation",
                calculation_logic="Exposed_Length_km = Sum(Geodesic_Length(ST_Intersection(Road.line, Hazard_Polygon)))",
                assumptions=[
                    "Road centerlines accurately represent highway alignment.",
                ],
                limitations=[
                    "Does not account for bridge elevation, embankments, or underpass topography.",
                    "Does not model traffic volume or moving vehicles.",
                ],
                spatial_resolution=SpatialResolution.ROAD_SEGMENT,
                temporal_basis="Static highway network database",
                quality_handling="Segments outside valid coordinate ranges flagged as INVALID.",
                uncertainty_description="Low length uncertainty when projected into metric CRS.",
                measures="Physical kilometers of road centerline passing through the hazard footprint.",
                does_not_measure="Road closure, traffic disruption, impassability, or pavement washout.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 5. Building Footprint Polygon Intersection
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-ASSET-POLY-001",
                method_name="Building Footprint Polygon Intersection & Count",
                method_version="1.0.0",
                exposure_type=ExposureType.BUILDING,
                input_dataset_type="Polygon Building Footprints",
                spatial_method="Polygon-Polygon Spatial Intersection (ST_Intersects / ST_Area)",
                calculation_logic="Exposed_Buildings = Count(Buildings intersecting Hazard_Polygon)",
                assumptions=[
                    "Footprint polygons accurately represent structural perimeter.",
                ],
                limitations=[
                    "Incomplete footprint datasets in peri-urban and rural areas.",
                    "Building height / number of stories is not factored into footprint count.",
                ],
                spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
                temporal_basis="Cadastral / OSM building layer",
                quality_handling="Missing footprint records treated as data gap, not zero buildings.",
                uncertainty_description="Variable completeness depending on regional mapping coverage.",
                measures="Number and total footprint area of physical structures intersecting the hazard polygon.",
                does_not_measure="Building occupancy, structural collapse, wall failure, or monetary damage.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 6. Agricultural Plot & Cropland Spatial Overlap
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-AGRI-PLOT-001",
                method_name="Agricultural Plot & Cropland Exposure Assessment",
                method_version="1.0.0",
                exposure_type=ExposureType.AGRICULTURE,
                input_dataset_type="Registered Farm Plots & Cropland Boundaries",
                spatial_method="Point-in-Polygon & Polygon Overlap Area Summation",
                calculation_logic="Exposed_Crop_Area_acres = Sum(Plot.area_acres for Plot in Intersecting_Plots)",
                assumptions=[
                    "Plot centroids and acreage declared during farmer onboarding reflect active cultivation.",
                ],
                limitations=[
                    "Fallow land or unplanted parcels within registered farms are not distinguished without satellite verification.",
                ],
                spatial_resolution=SpatialResolution.POINT,
                temporal_basis="Seasonal farmer registry",
                quality_handling="Unregistered cropland areas reported as unmonitored; never fabricated.",
                uncertainty_description="Acreage precision based on farmer self-reporting or GPS demarcation.",
                measures="Cultivated land area and crop types geographically situated inside the hazard footprint.",
                does_not_measure="Yield reduction, lodging damage, crop submergence mortality, or financial loss.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )

        # 7. Administrative Boundary Geographic Overlap
        self.register_method(
            ExposureMethod(
                method_id="EXP-METH-ADMIN-AREA-001",
                method_name="Administrative Boundary Geographic Overlap Quantification",
                method_version="1.0.0",
                exposure_type=ExposureType.ADMINISTRATIVE_ASSET,
                input_dataset_type="MultiPolygon Administrative Boundaries (States, Districts, Sub-districts)",
                spatial_method="PostGIS Geodesic Clipping (ST_Intersection, ST_Area)",
                calculation_logic="Exposed_Area_sqkm = Geodesic_Area(ST_Intersection(Admin_Geom, Hazard_Geom))",
                assumptions=[
                    "Survey of India / LGD administrative boundary geometries are authoritative.",
                ],
                limitations=[
                    "Administrative area exposure is a geographic metric, not a demographic or economic metric.",
                ],
                spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
                temporal_basis="Survey of India / Census 2011 / LGD 2024",
                quality_handling="Topology errors corrected via ST_MakeValid; invalid geometries rejected.",
                uncertainty_description="Sub-meter geodesic boundary precision.",
                measures="Total square kilometers and percentage of an administrative unit covered by the hazard.",
                does_not_measure="Severity of impact within the administrative area.",
                status=ExposureMethodStatus.ACTIVE,
            )
        )


# Global singleton instance
exposure_method_registry = ExposureMethodRegistry()
