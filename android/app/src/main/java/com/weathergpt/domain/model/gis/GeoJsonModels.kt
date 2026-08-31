package com.weathergpt.domain.model.gis

/**
 * Clean Domain representations of RFC 7946 GeoJSON structures.
 *
 * CRITICAL INVARIANT:
 * Coordinates inside all GeoJSON domain models strictly retain the standard
 * GeoJSON convention: [longitude, latitude] in EPSG:4326.
 *
 * Conversion to UI/Renderer representations (e.g. MapLatLng(lat, lon)) is handled
 * exclusively by map adapters at the presentation boundary.
 */

sealed class GeoJsonGeometry {
    abstract val type: String

    data class Point(
        val longitude: Double,
        val latitude: Double
    ) : GeoJsonGeometry() {
        override val type: String = "Point"
    }

    data class Polygon(
        /**
         * List of linear rings. The first ring is the exterior boundary.
         * Subsequent rings are interior holes. Each coordinate pair is (longitude, latitude).
         */
        val rings: List<List<Pair<Double, Double>>>
    ) : GeoJsonGeometry() {
        override val type: String = "Polygon"
    }

    data class MultiPolygon(
        /**
         * List of polygons, each containing linear rings of (longitude, latitude).
         */
        val polygons: List<List<List<Pair<Double, Double>>>>
    ) : GeoJsonGeometry() {
        override val type: String = "MultiPolygon"
    }

    data class LineString(
        val coordinates: List<Pair<Double, Double>>
    ) : GeoJsonGeometry() {
        override val type: String = "LineString"
    }

    data class Unknown(
        override val type: String
    ) : GeoJsonGeometry()
}

data class GeoJsonFeature(
    val id: String?,
    val geometry: GeoJsonGeometry?,
    val properties: Map<String, String>,
    val bbox: List<Double>? = null
)

data class GeoJsonFeatureCollection(
    val features: List<GeoJsonFeature>,
    val bbox: List<Double>? = null
)
