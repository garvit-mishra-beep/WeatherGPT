package com.weathergpt.data.remote.dto.gis

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

/**
 * Standard RFC 7946 GeoJSON representations for mobile consumption.
 * Coordinates are strictly [longitude, latitude] in EPSG:4326.
 */
@Serializable
data class GeoJsonGeometryDto(
    @SerialName("type")
    val type: String,
    // Flexible representation: Point [lon, lat], Polygon [[[lon, lat], ...]], MultiPolygon [[[[lon, lat], ...]]]
    @SerialName("coordinates")
    val coordinates: kotlinx.serialization.json.JsonElement? = null
)

@Serializable
data class GeoJsonFeatureDto(
    @SerialName("type")
    val type: String = "Feature",
    @SerialName("id")
    val id: String? = null,
    @SerialName("geometry")
    val geometry: GeoJsonGeometryDto? = null,
    @SerialName("properties")
    val properties: JsonObject? = null,
    @SerialName("bbox")
    val bbox: List<Double>? = null
)

@Serializable
data class GeoJsonFeatureCollectionDto(
    @SerialName("type")
    val type: String = "FeatureCollection",
    @SerialName("features")
    val features: List<GeoJsonFeatureDto> = emptyList(),
    @SerialName("bbox")
    val bbox: List<Double>? = null
)
