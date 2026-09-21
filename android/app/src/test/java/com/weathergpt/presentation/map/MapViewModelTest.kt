package com.weathergpt.presentation.map

import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.gis.BoundaryUnit
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapLayer
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.map.MapViewport
import com.weathergpt.domain.repository.WeatherGPTRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class MapViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    private fun createProxyRepository(): WeatherGPTRepository {
        val handler = java.lang.reflect.InvocationHandler { _, method, args ->
            when (method.name) {
                "getPointWeatherMap" -> {
                    val lat = args?.getOrNull(0) as? Double ?: 22.72
                    val lon = args?.getOrNull(1) as? Double ?: 78.65
                    ResultState.Success(
                        MapSpecification(
                            id = "map_pt",
                            title = "Point Weather Map",
                            viewport = MapViewport(centerLongitude = lon, centerLatitude = lat, zoom = 5.0),
                            layers = listOf(MapLayer(id = "layer1", name = "Radar", type = "raster")),
                            legend = listOf(LegendItem("Rain", "#00F", "0-10"))
                        )
                    )
                }
                "getRiskMap" -> {
                    val lat = args?.getOrNull(0) as? Double ?: 22.72
                    val lon = args?.getOrNull(1) as? Double ?: 78.65
                    ResultState.Success(
                        MapSpecification(
                            id = "map_risk",
                            title = "Risk Map",
                            viewport = MapViewport(centerLongitude = lon, centerLatitude = lat, zoom = 5.0),
                            layers = listOf(MapLayer(id = "risk_layer", name = "Risk", type = "fill")),
                            legend = listOf(LegendItem("High Risk", "#F00", "> 8.0"))
                        )
                    )
                }
                "getLocationHierarchy" -> {
                    val lat = args?.getOrNull(0) as? Double ?: 22.72
                    val lon = args?.getOrNull(1) as? Double ?: 78.65
                    val distName = when {
                        Math.abs(lat - 28.6139) < 0.1 -> "Delhi"
                        Math.abs(lat - 19.0760) < 0.1 -> "Mumbai"
                        Math.abs(lat - 13.0827) < 0.1 -> "Chennai"
                        else -> "Indore"
                    }
                    ResultState.Success(
                        LocationHierarchy(
                            latitude = lat,
                            longitude = lon,
                            isResolved = true,
                            country = BoundaryUnit(code = "IND", name = "India", level = "country", parentCode = null, areaSqkm = 3287263.0),
                            state = BoundaryUnit(code = "ST", name = "State", level = "state", parentCode = "IND", areaSqkm = 308252.0),
                            district = BoundaryUnit(code = "DIST", name = distName, level = "district", parentCode = "ST", areaSqkm = 3898.0),
                            subdistrict = null
                        )
                    )
                }
                else -> ResultState.Success(Unit)
            }
        }
        return Proxy.newProxyInstance(
            WeatherGPTRepository::class.java.classLoader,
            arrayOf(WeatherGPTRepository::class.java),
            handler
        ) as WeatherGPTRepository
    }

    private val repository = createProxyRepository()
    private val locationManager = SharedLocationManager(null)

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialCenterAndDefaultCities() = runTest {
        val defaultState = MapUiState()
        assertEquals(22.72, defaultState.centerCoordinates.latitude, 0.01)
        assertEquals(78.65, defaultState.centerCoordinates.longitude, 0.01)
        assertEquals(5.0, defaultState.zoomLevel, 0.01)

        val cityNames = defaultState.defaultCities.map { it.name }
        assertTrue(cityNames.contains("Indore"))
        assertTrue(cityNames.contains("Delhi"))
        assertTrue(cityNames.contains("Mumbai"))
        assertTrue(cityNames.contains("Chennai"))

        val indore = defaultState.defaultCities.first { it.name == "Indore" }
        assertEquals(22.7196, indore.latitude, 0.001)
        assertEquals(75.8577, indore.longitude, 0.001)
    }

    @Test
    fun testWeatherVisualMapping() {
        assertEquals("☀️", MapViewModel.getWeatherVisual(0))
        assertEquals("⛅", MapViewModel.getWeatherVisual(2))
        assertEquals("☁️", MapViewModel.getWeatherVisual(3))
        assertEquals("🌫️", MapViewModel.getWeatherVisual(45))
        assertEquals("🌫️", MapViewModel.getWeatherVisual(48))
        assertEquals("🌦️", MapViewModel.getWeatherVisual(51))
        assertEquals("🌧️", MapViewModel.getWeatherVisual(61))
        assertEquals("🌧️", MapViewModel.getWeatherVisual(80))
        assertEquals("🌨️", MapViewModel.getWeatherVisual(71))
        assertEquals("⛈️", MapViewModel.getWeatherVisual(95))
        assertEquals("⛈️", MapViewModel.getWeatherVisual(99))
    }

    @Test
    fun testOnLocationSelected() = runTest {
        val viewModel = MapViewModel(repository, locationManager)
        advanceUntilIdle()

        viewModel.onLocationSelected(28.6139, 77.2090, "Delhi")
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals(28.6139, state.centerCoordinates.latitude, 0.001)
        assertEquals(77.2090, state.centerCoordinates.longitude, 0.001)
        assertEquals("Delhi", state.selectedCityName)
    }

    @Test
    fun testSelectDefaultCity() = runTest {
        val viewModel = MapViewModel(repository, locationManager)
        advanceUntilIdle()

        val mumbai = MapCity("Mumbai", 19.0760, 72.8777)
        viewModel.selectCity(mumbai)
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals(19.0760, state.centerCoordinates.latitude, 0.001)
        assertEquals(72.8777, state.centerCoordinates.longitude, 0.001)
        assertEquals("Mumbai", state.selectedCityName)
    }

    @Test
    fun testLayerSwitching() = runTest {
        val viewModel = MapViewModel(repository, locationManager)
        advanceUntilIdle()

        viewModel.setLayer(WeatherMapLayer.TEMPERATURE)
        advanceUntilIdle()
        assertEquals(WeatherMapLayer.TEMPERATURE, viewModel.uiState.value.selectedLayer)

        viewModel.setLayer(WeatherMapLayer.RISK)
        advanceUntilIdle()
        assertEquals(WeatherMapLayer.RISK, viewModel.uiState.value.selectedLayer)
    }
}
