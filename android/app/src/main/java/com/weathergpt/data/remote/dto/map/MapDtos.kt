package com.weathergpt.data.remote.dto.map

import com.weathergpt.data.remote.dto.gis.GeoJsonFeatureCollectionDto
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class MapViewportDto(
    @SerialName("center")
    val center: List<Double> = listOf(78.9629, 20.5937), // [longitude, latitude] in EPSG:4326
    @SerialName("zoom")
    val zoom: Double = 8.5,
    @SerialName("pitch")
    val pitch: Double = 0.0,
    @SerialName("bearing")
    val bearing: Double = 0.0,
    @SerialName("bbox")
    val bbox: List<Double>? = null // [min_lon, min_lat, max_lon, max_lat]
)

@Serializable
data class MapStyleDto(
    @SerialName("fill_color")
    val fillColor: String? = null,
    @SerialName("fill_opacity")
    val fillOpacity: Double? = null,
    @SerialName("stroke_color")
    val strokeColor: String? = null,
    @SerialName("stroke_width")
    val strokeWidth: Double? = null,
    @SerialName("point_radius")
    val pointRadius: Double? = null,
    @SerialName("icon_name")
    val iconName: String? = null
)

@Serializable
data class MapLayerDto(
    @SerialName("id")
    val id: String,
    @SerialName("name")
    val name: String? = null,
    @SerialName("title")
    val title: String? = null,
    @SerialName("type")
    val type: String, // "circle", "fill", "line", "symbol", "raster", "geojson"
    @SerialName("source_id")
    val sourceId: String? = null,
    @SerialName("source_type")
    val sourceType: String? = "geojson",
    @SerialName("source_data")
    val sourceData: GeoJsonFeatureCollectionDto? = null,
    @SerialName("geojson")
    val geojson: GeoJsonFeatureCollectionDto? = null,
    @SerialName("paint")
    val paint: JsonObject? = null,
    @SerialName("style")
    val style: MapStyleDto? = null,
    @SerialName("layout")
    val layout: JsonObject? = null,
    @SerialName("min_zoom")
    val minZoom: Double? = null,
    @SerialName("max_zoom")
    val maxZoom: Double? = null,
    @SerialName("visible")
    val visible: Boolean = true
)

@Serializable
data class LegendItemDto(
    @SerialName("label")
    val label: String,
    @SerialName("color")
    val color: String,
    @SerialName("value_range")
    val valueRange: String? = null,
    @SerialName("description")
    val description: String? = null,
    @SerialName("hazard_type")
    val hazardType: String? = null,
    @SerialName("official_level")
    val officialLevel: String? = null
)

@Serializable
data class MapLegendDto(
    @SerialName("title")
    val title: String = "Map Legend",
    @SerialName("items")
    val items: List<LegendItemDto> = emptyList()
)

@Serializable
data class MapSpecificationDto(
    @SerialName("type")
    val type: String = "map_specification",
    @SerialName("id")
    val id: String? = null,
    @SerialName("map_id")
    val mapId: String? = null,
    @SerialName("title")
    val title: String = "WeatherGPT Map",
    @SerialName("viewport")
    val viewport: MapViewportDto? = null,
    @SerialName("center")
    val center: List<Double>? = null, // fallback [lon, lat]
    @SerialName("zoom")
    val zoom: Double? = null,
    @SerialName("bbox")
    val bbox: List<Double>? = null, // fallback [min_lon, min_lat, max_lon, max_lat]
    @SerialName("layers")
    val layers: List<MapLayerDto> = emptyList(),
    @SerialName("legend")
    val legend: List<LegendItemDto> = emptyList(),
    @SerialName("provenance")
    val provenance: JsonObject? = null,
    @SerialName("quality")
    val quality: String = "AVAILABLE"
)

@Serializable
data class WarningMapRequestDto(
    @SerialName("warning_geometry")
    val warningGeometry: JsonObject,
    @SerialName("alert_id")
    val alertId: String = "WARN-CAP-001",
    @SerialName("event")
    val event: String = "Severe Weather Alert",
    @SerialName("severity")
    val severity: String = "Orange"
)

@Serializable
data class RiskMapRequestDto(
    @SerialName("latitude")
    val latitude: Double? = null,
    @SerialName("longitude")
    val longitude: Double? = null,
    @SerialName("district_code")
    val districtCode: String? = null,
    @SerialName("observed_rain_mm")
    val observedRainMm: Double? = null,
    @SerialName("observed_wind_kmh")
    val observedWindKmh: Double? = null
)
