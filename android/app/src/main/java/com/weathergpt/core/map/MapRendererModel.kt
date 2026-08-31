package com.weathergpt.core.map

import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapStyle

/**
 * Standard presentation / renderer coordinate representation.
 *
 * CRITICAL NOTE ON CONVENTIONS:
 * - Backend / GeoJSON convention: [longitude, latitude] in EPSG:4326.
 * - Mobile / Map SDK convention: latitude, longitude.
 *
 * [MapLatLng] encapsulates the renderer convention while keeping domain GeoJSON intact.
 */
data class MapLatLng(
    val latitude: Double,
    val longitude: Double
)

/**
 * Bounding envelope for camera framing in mobile renderers.
 */
data class MapBounds(
    val southWest: MapLatLng,
    val northEast: MapLatLng
)

/**
 * Renderable geometries extracted and prepared for mobile canvas/map rendering.
 */
sealed class RenderableGeometry {

    data class Point(
        val position: MapLatLng,
        val title: String? = null,
        val properties: Map<String, String> = emptyMap()
    ) : RenderableGeometry()

    data class Polygon(
        val outerRing: List<MapLatLng>,
        val holes: List<List<MapLatLng>> = emptyList(),
        val fillColor: String? = null,
        val fillOpacity: Double? = null,
        val strokeColor: String? = null,
        val strokeWidth: Double? = null
    ) : RenderableGeometry()

    data class MultiPolygon(
        val polygons: List<Polygon>
    ) : RenderableGeometry()

    data class LineString(
        val points: List<MapLatLng>,
        val strokeColor: String? = null,
        val strokeWidth: Double? = null
    ) : RenderableGeometry()
}

/**
 * Renderable layer ready for mobile Map SDK consumption (e.g. MapLibre GL, Leaflet WebView, or Canvas).
 */
data class RenderableLayer(
    val id: String,
    val name: String,
    val type: String,
    val geometries: List<RenderableGeometry> = emptyList(),
    val style: MapStyle? = null,
    val visible: Boolean = true
)

/**
 * Complete presentation-ready Map Specification model decoupled from any specific Map SDK.
 */
data class RenderableMapSpecification(
    val id: String,
    val title: String,
    val center: MapLatLng,
    val zoom: Double,
    val bounds: MapBounds? = null,
    val layers: List<RenderableLayer> = emptyList(),
    val legend: List<LegendItem> = emptyList(),
    val quality: String = "AVAILABLE"
)
