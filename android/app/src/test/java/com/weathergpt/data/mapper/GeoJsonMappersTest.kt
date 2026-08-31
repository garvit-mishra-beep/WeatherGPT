package com.weathergpt.data.mapper

import com.weathergpt.core.network.networkJson
import com.weathergpt.data.mapper.Mappers.toDomain
import com.weathergpt.data.remote.dto.gis.GeoJsonFeatureCollectionDto
import com.weathergpt.data.remote.dto.gis.GeoJsonGeometryDto
import com.weathergpt.data.remote.dto.map.MapSpecificationDto
import com.weathergpt.domain.model.gis.GeoJsonGeometry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GeoJsonMappersTest {

    @Test
    fun `parse Point geometry preserves exact longitude latitude coordinates`() {
        val json = """
            {
                "type": "Point",
                "coordinates": [72.8311, 21.1702]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<GeoJsonGeometryDto>(json)
        val domain = dto.toDomain()

        assertTrue(domain is GeoJsonGeometry.Point)
        val pt = domain as GeoJsonGeometry.Point
        assertEquals(72.8311, pt.longitude, 0.0001)
        assertEquals(21.1702, pt.latitude, 0.0001)
    }

    @Test
    fun `parse Polygon geometry preserves outer rings and coordinate pairs`() {
        val json = """
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [68.0, 20.0],
                        [75.0, 20.0],
                        [75.0, 25.0],
                        [68.0, 25.0],
                        [68.0, 20.0]
                    ]
                ]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<GeoJsonGeometryDto>(json)
        val domain = dto.toDomain()

        assertTrue(domain is GeoJsonGeometry.Polygon)
        val poly = domain as GeoJsonGeometry.Polygon
        assertEquals(1, poly.rings.size)
        assertEquals(5, poly.rings[0].size)
        assertEquals(68.0, poly.rings[0][0].first, 0.0001) // longitude
        assertEquals(20.0, poly.rings[0][0].second, 0.0001) // latitude
    }

    @Test
    fun `parse MultiPolygon geometry correctly extracts multiple polygonal parts`() {
        val json = """
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [70.0, 20.0],
                            [71.0, 20.0],
                            [71.0, 21.0],
                            [70.0, 20.0]
                        ]
                    ],
                    [
                        [
                            [72.0, 22.0],
                            [73.0, 22.0],
                            [73.0, 23.0],
                            [72.0, 22.0]
                        ]
                    ]
                ]
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<GeoJsonGeometryDto>(json)
        val domain = dto.toDomain()

        assertTrue(domain is GeoJsonGeometry.MultiPolygon)
        val multi = domain as GeoJsonGeometry.MultiPolygon
        assertEquals(2, multi.polygons.size)
        assertEquals(4, multi.polygons[0][0].size)
        assertEquals(70.0, multi.polygons[0][0][0].first, 0.0001)
        assertEquals(20.0, multi.polygons[0][0][0].second, 0.0001)
    }

    @Test
    fun `parse MapSpecification with viewport, layers, and legend matches backend contract`() {
        val json = """
            {
                "type": "map_specification",
                "id": "map_spec_01",
                "title": "Severe Weather Warning Map",
                "viewport": {
                    "center": [72.8311, 21.1702],
                    "zoom": 8.5,
                    "pitch": 0.0,
                    "bearing": 0.0,
                    "bbox": [72.0, 20.5, 73.5, 22.0]
                },
                "layers": [
                    {
                        "id": "warning_polygon_layer",
                        "name": "Orange Warning Zone",
                        "type": "fill",
                        "source_id": "warn_src",
                        "source_type": "geojson",
                        "source_data": {
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "id": "feat_warn_01",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": [72.8311, 21.1702]
                                    },
                                    "properties": {
                                        "severity": "Orange",
                                        "hazard": "Heavy Rainfall"
                                    }
                                }
                            ]
                        },
                        "paint": {
                            "fill-color": "#FF9800",
                            "fill-opacity": "0.4"
                        },
                        "visible": true
                    }
                ],
                "legend": [
                    {
                        "label": "Orange Alert",
                        "color": "#FF9800",
                        "value_range": null,
                        "hazard_type": "Heavy Rainfall",
                        "official_level": "Orange"
                    }
                ],
                "provenance": {
                    "authority": "India Meteorological Department (IMD)"
                },
                "quality": "AVAILABLE"
            }
        """.trimIndent()

        val dto = networkJson.decodeFromString<MapSpecificationDto>(json)
        val domain = dto.toDomain()

        assertEquals("map_spec_01", domain.id)
        assertEquals("Severe Weather Warning Map", domain.title)
        assertEquals(72.8311, domain.viewport.centerLongitude, 0.0001)
        assertEquals(21.1702, domain.viewport.centerLatitude, 0.0001)
        assertEquals(8.5, domain.viewport.zoom, 0.01)

        assertEquals(1, domain.layers.size)
        val layer = domain.layers[0]
        assertEquals("warning_polygon_layer", layer.id)
        assertEquals("Orange Warning Zone", layer.name)
        assertEquals("fill", layer.type)
        assertNotNull(layer.sourceData)
        assertEquals(1, layer.sourceData!!.features.size)

        assertEquals(1, domain.legend.size)
        val legendItem = domain.legend[0]
        assertEquals("Orange Alert", legendItem.label)
        assertEquals("#FF9800", legendItem.color)
        assertEquals("Orange", legendItem.officialLevel)

        assertEquals("India Meteorological Department (IMD)", domain.provenance["authority"])
        assertEquals("AVAILABLE", domain.quality)
    }
}
