package com.weathergpt.core.map

import com.weathergpt.domain.model.gis.GeoJsonFeature
import com.weathergpt.domain.model.gis.GeoJsonGeometry
import com.weathergpt.domain.model.map.MapLayer
import com.weathergpt.domain.model.map.MapSpecification

/**
 * Dedicated Adapter converting pure domain [MapSpecification] into presentation-ready
 * [RenderableMapSpecification].
 *
 * CRITICAL COORDINATE TRANSFORMATION:
 * GeoJSON coordinate pairs are strictly (longitude, latitude).
 * Renderer [MapLatLng] pairs are strictly (latitude, longitude).
 *
 * This adapter is the ONLY boundary where coordinate orientation is transformed for
 * mobile map SDK presentation, preserving backend GeoJSON integrity.
 */
object MapRendererAdapter {

    fun toRenderable(specification: MapSpecification): RenderableMapSpecification {
        val centerLatLng = MapLatLng(
            latitude = specification.viewport.centerLatitude,
            longitude = specification.viewport.centerLongitude
        )

        val bounds = specification.viewport.bbox?.let { bbox ->
            if (bbox.size >= 4) {
                val minLon = bbox[0]
                val minLat = bbox[1]
                val maxLon = bbox[2]
                val maxLat = bbox[3]
                MapBounds(
                    southWest = MapLatLng(latitude = minLat, longitude = minLon),
                    northEast = MapLatLng(latitude = maxLat, longitude = maxLon)
                )
            } else null
        }

        val renderableLayers = specification.layers.map { layer ->
            toRenderableLayer(layer)
        }

        return RenderableMapSpecification(
            id = specification.id,
            title = specification.title,
            center = centerLatLng,
            zoom = specification.viewport.zoom,
            bounds = bounds,
            layers = renderableLayers,
            legend = specification.legend,
            quality = specification.quality
        )
    }

    private fun toRenderableLayer(layer: MapLayer): RenderableLayer {
        val geometries = mutableListOf<RenderableGeometry>()

        layer.sourceData?.features?.forEach { feature ->
            val featureGeometry = toRenderableGeometry(feature)
            if (featureGeometry != null) {
                geometries.add(featureGeometry)
            }
        }

        return RenderableLayer(
            id = layer.id,
            name = layer.name,
            type = layer.type,
            geometries = geometries,
            style = layer.style,
            visible = layer.visible
        )
    }

    private fun toRenderableGeometry(feature: GeoJsonFeature): RenderableGeometry? {
        val geometry = feature.geometry ?: return null

        return when (geometry) {
            is GeoJsonGeometry.Point -> {
                RenderableGeometry.Point(
                    position = MapLatLng(
                        latitude = geometry.latitude,
                        longitude = geometry.longitude
                    ),
                    title = feature.id,
                    properties = feature.properties
                )
            }
            is GeoJsonGeometry.Polygon -> {
                val outerRing = geometry.rings.firstOrNull()?.map { coord ->
                    MapLatLng(latitude = coord.second, longitude = coord.first)
                } ?: emptyList()

                val holes = if (geometry.rings.size > 1) {
                    geometry.rings.drop(1).map { ring ->
                        ring.map { coord -> MapLatLng(latitude = coord.second, longitude = coord.first) }
                    }
                } else emptyList()

                RenderableGeometry.Polygon(
                    outerRing = outerRing,
                    holes = holes
                )
            }
            is GeoJsonGeometry.MultiPolygon -> {
                val polygons = geometry.polygons.map { polyRings ->
                    val outer = polyRings.firstOrNull()?.map { coord ->
                        MapLatLng(latitude = coord.second, longitude = coord.first)
                    } ?: emptyList()

                    val inner = if (polyRings.size > 1) {
                        polyRings.drop(1).map { ring ->
                            ring.map { coord -> MapLatLng(latitude = coord.second, longitude = coord.first) }
                        }
                    } else emptyList()

                    RenderableGeometry.Polygon(outerRing = outer, holes = inner)
                }

                RenderableGeometry.MultiPolygon(
                    polygons = polygons
                )
            }
            is GeoJsonGeometry.LineString -> {
                val points = geometry.coordinates.map { coord ->
                    MapLatLng(latitude = coord.second, longitude = coord.first)
                }
                RenderableGeometry.LineString(points = points)
            }
            is GeoJsonGeometry.Unknown -> null
        }
    }
}

/**
 * Clean renderer abstraction allowing the map SDK (MapLibre GL, Leaflet, Canvas)
 * to be plugged in without coupling domain or presentation architecture.
 */
interface MapRenderer {
    fun renderMap(specification: RenderableMapSpecification)
    fun setCenter(center: MapLatLng, zoom: Double)
    fun clearLayers()
}
