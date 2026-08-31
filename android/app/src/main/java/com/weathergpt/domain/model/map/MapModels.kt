package com.weathergpt.domain.model.map

import com.weathergpt.domain.model.gis.GeoJsonFeatureCollection

data class MapViewport(
    val centerLongitude: Double,
    val centerLatitude: Double,
    val zoom: Double,
    val pitch: Double = 0.0,
    val bearing: Double = 0.0,
    val bbox: List<Double>? = null
)

data class MapStyle(
    val fillColor: String? = null,
    val fillOpacity: Double? = null,
    val strokeColor: String? = null,
    val strokeWidth: Double? = null,
    val pointRadius: Double? = null,
    val iconName: String? = null
)

data class MapLayer(
    val id: String,
    val name: String,
    val type: String, // "circle", "fill", "line", "symbol", "raster", "geojson"
    val sourceId: String? = null,
    val sourceData: GeoJsonFeatureCollection? = null,
    val paint: Map<String, String> = emptyMap(),
    val style: MapStyle? = null,
    val visible: Boolean = true
) {
    val title: String get() = name
}

data class LegendItem(
    val label: String,
    val color: String,
    val valueRange: String? = null,
    val description: String? = null,
    val hazardType: String? = null,
    val officialLevel: String? = null
)

data class MapLegend(
    val title: String = "Map Legend",
    val items: List<LegendItem>
)

data class MapSpecification(
    val id: String,
    val title: String,
    val viewport: MapViewport,
    val layers: List<MapLayer> = emptyList(),
    val legend: List<LegendItem> = emptyList(),
    val provenance: Map<String, String> = emptyMap(),
    val quality: String = "AVAILABLE"
) {
    // Backwards-compatible convenience accessors
    val mapId: String get() = id
    val centerLongitude: Double get() = viewport.centerLongitude
    val centerLatitude: Double get() = viewport.centerLatitude
    val zoom: Double get() = viewport.zoom
    val bbox: List<Double>? get() = viewport.bbox
}
