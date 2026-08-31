package com.weathergpt.core.map

import com.weathergpt.domain.model.gis.GeoJsonFeature
import com.weathergpt.domain.model.gis.GeoJsonFeatureCollection
import com.weathergpt.domain.model.gis.GeoJsonGeometry
import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapLayer
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.map.MapViewport
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MapRendererAdapterTest {

    @Test
    fun `GeoJSON coordinates convert to MapLatLng without mutating domain geometry`() {
        // Domain GeoJSON strictly uses [longitude, latitude] in EPSG:4326
        val lon = 72.8311
        val lat = 21.1702

        val pointGeometry = GeoJsonGeometry.Point(longitude = lon, latitude = lat)
        val feature = GeoJsonFeature(
            id = "feat_surat_pt",
            geometry = pointGeometry,
            properties = mapOf("district" to "Surat", "temp_c" to "31.2")
        )
        val layer = MapLayer(
            id = "weather_point_layer",
            name = "Weather Point",
            type = "circle",
            sourceData = GeoJsonFeatureCollection(features = listOf(feature))
        )
        val spec = MapSpecification(
            id = "map_surat",
            title = "Surat Weather Map",
            viewport = MapViewport(
                centerLongitude = lon,
                centerLatitude = lat,
                zoom = 10.0,
                bbox = listOf(72.5, 21.0, 73.0, 21.5)
            ),
            layers = listOf(layer),
            legend = listOf(
                LegendItem(label = "Moderate Rain", color = "#2196F3", valueRange = "2.5 - 7.5 mm/h")
            )
        )

        val renderable = MapRendererAdapter.toRenderable(spec)

        // Verify MapLatLng has latitude and longitude correctly extracted
        assertEquals(lat, renderable.center.latitude, 0.0001)
        assertEquals(lon, renderable.center.longitude, 0.0001)
        assertEquals(10.0, renderable.zoom, 0.01)

        // Verify bounds: [min_lon, min_lat, max_lon, max_lat] -> southWest(min_lat, min_lon), northEast(max_lat, max_lon)
        assertNotNull(renderable.bounds)
        assertEquals(21.0, renderable.bounds!!.southWest.latitude, 0.0001)
        assertEquals(72.5, renderable.bounds!!.southWest.longitude, 0.0001)
        assertEquals(21.5, renderable.bounds!!.northEast.latitude, 0.0001)
        assertEquals(73.0, renderable.bounds!!.northEast.longitude, 0.0001)

        // Verify layer geometry extraction
        assertEquals(1, renderable.layers.size)
        val renderableLayer = renderable.layers[0]
        assertEquals(1, renderableLayer.geometries.size)
        assertTrue(renderableLayer.geometries[0] is RenderableGeometry.Point)

        val renderablePt = renderableLayer.geometries[0] as RenderableGeometry.Point
        assertEquals(lat, renderablePt.position.latitude, 0.0001)
        assertEquals(lon, renderablePt.position.longitude, 0.0001)
        assertEquals("Surat", renderablePt.properties["district"])

        // CRITICAL INVARIANT: Original domain geometry is untouched
        assertEquals(lon, pointGeometry.longitude, 0.0001)
        assertEquals(lat, pointGeometry.latitude, 0.0001)
    }

    @Test
    fun `polygon linear rings correctly map to outer ring and holes`() {
        val outerRing = listOf(
            Pair(72.0, 21.0),
            Pair(73.0, 21.0),
            Pair(73.0, 22.0),
            Pair(72.0, 22.0),
            Pair(72.0, 21.0)
        )
        val holeRing = listOf(
            Pair(72.3, 21.3),
            Pair(72.7, 21.3),
            Pair(72.7, 21.7),
            Pair(72.3, 21.7),
            Pair(72.3, 21.3)
        )

        val polyGeom = GeoJsonGeometry.Polygon(rings = listOf(outerRing, holeRing))
        val feature = GeoJsonFeature(id = "poly_feat", geometry = polyGeom, properties = emptyMap())
        val layer = MapLayer(
            id = "hazard_zone",
            name = "Hazard Zone",
            type = "fill",
            sourceData = GeoJsonFeatureCollection(features = listOf(feature))
        )
        val spec = MapSpecification(
            id = "map_poly",
            title = "Polygon Map",
            viewport = MapViewport(centerLongitude = 72.5, centerLatitude = 21.5, zoom = 8.0),
            layers = listOf(layer)
        )

        val renderable = MapRendererAdapter.toRenderable(spec)
        val rLayer = renderable.layers[0]
        val rGeom = rLayer.geometries[0] as RenderableGeometry.Polygon

        assertEquals(5, rGeom.outerRing.size)
        assertEquals(21.0, rGeom.outerRing[0].latitude, 0.0001)
        assertEquals(72.0, rGeom.outerRing[0].longitude, 0.0001)

        assertEquals(1, rGeom.holes.size)
        assertEquals(5, rGeom.holes[0].size)
        assertEquals(21.3, rGeom.holes[0][0].latitude, 0.0001)
        assertEquals(72.3, rGeom.holes[0][0].longitude, 0.0001)
    }
}
