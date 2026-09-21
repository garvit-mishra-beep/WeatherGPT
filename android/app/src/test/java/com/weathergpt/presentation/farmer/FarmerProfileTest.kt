package com.weathergpt.presentation.farmer

import com.weathergpt.core.location.SharedLocationManager
import com.weathergpt.core.result.ResultState
import com.weathergpt.data.local.InMemoryLocalWeatherDataSource
import com.weathergpt.domain.model.farmer.FarmerProfile
import com.weathergpt.domain.repository.WeatherGPTRepository
import com.weathergpt.presentation.ViewModelsTest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class FarmerProfileTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var localDataSource: InMemoryLocalWeatherDataSource
    private lateinit var locationManager: SharedLocationManager

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        localDataSource = InMemoryLocalWeatherDataSource()
        locationManager = SharedLocationManager()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `data source saves and retrieves farmer profile with high fidelity`() = runTest {
        val initialProfile = localDataSource.getFarmerProfile()
        assertNotNull(initialProfile)
        assertEquals("Gwalior Farmer", initialProfile?.fullName)

        val updatedProfile = FarmerProfile(
            fullName = "Harish Sharma",
            mobileNumber = "9876543210",
            village = "Morar",
            district = "Gwalior",
            state = "Madhya Pradesh",
            pincode = "474006",
            fieldName = "Plot A",
            plotNumber = "12/4",
            surveyNumber = "S-88",
            farmArea = 3.5,
            areaUnit = "hectare",
            crop = "Mustard",
            variety = "Pusa Bold",
            cropStage = "Flowering",
            sowingDate = "2026-10-15",
            expectedHarvestDate = "2027-02-20",
            soilType = "Alluvial",
            soilMoistureAvailability = "Irrigated",
            irrigationType = "Drip",
            farmingActivity = "Crop Production",
            preferredLanguage = "Hindi",
            temperatureUnit = "Celsius",
            notificationsEnabled = true
        )

        val saveRowId = localDataSource.saveFarmerProfile(updatedProfile)
        assertTrue(saveRowId > 0)

        val retrieved = localDataSource.getFarmerProfile()
        assertNotNull(retrieved)
        assertEquals("Harish Sharma", retrieved?.fullName)
        assertEquals("Mustard", retrieved?.crop)
        assertEquals("Flowering", retrieved?.cropStage)
        assertEquals(3.5, retrieved?.farmArea ?: 0.0, 0.001)
        assertEquals("Alluvial", retrieved?.soilType)
        assertEquals("Drip", retrieved?.irrigationType)
    }

    @Test
    fun `viewModel validates required fields accurately`() = runTest {
        val fakeRepo = object : WeatherGPTRepository by ViewModelsTest.createFakeRepository() {
            override suspend fun getFarmerProfile(): ResultState<FarmerProfile> =
                ResultState.Success(localDataSource.getFarmerProfile() ?: FarmerProfile())

            override suspend fun saveFarmerProfile(profile: FarmerProfile): ResultState<Unit> {
                localDataSource.saveFarmerProfile(profile)
                return ResultState.Success(Unit)
            }
        }

        val viewModel = FarmerProfileViewModel(fakeRepo, locationManager)
        advanceUntilIdle()

        // Test invalid area
        viewModel.setFieldArea("invalid_num")
        var saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("Please enter a valid positive field area", viewModel.uiState.value.validationError)

        viewModel.setFieldArea("0")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("Please enter a valid positive field area", viewModel.uiState.value.validationError)

        viewModel.setFieldArea("2.5")

        // Test required Full Name
        viewModel.setFullName("")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("Full Name is required", viewModel.uiState.value.validationError)

        viewModel.setFullName("Shivraj Singh")

        // Test required District
        viewModel.setDistrict("")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("District is required", viewModel.uiState.value.validationError)

        viewModel.setDistrict("Gwalior")

        // Test required State
        viewModel.setState("")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("State is required", viewModel.uiState.value.validationError)

        viewModel.setState("Madhya Pradesh")

        // Test required Crop
        viewModel.setCrop("")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("Crop is required", viewModel.uiState.value.validationError)

        viewModel.setCrop("Wheat")

        // Test required Crop Stage
        viewModel.setCropStage("")
        saved = viewModel.saveProfile()
        assertFalse(saved)
        assertEquals("Crop Stage is required", viewModel.uiState.value.validationError)

        viewModel.setCropStage("Vegetative")

        // Valid submission
        saved = viewModel.saveProfile()
        advanceUntilIdle()
        assertTrue(saved)
        assertNull(viewModel.uiState.value.validationError)
        assertTrue(viewModel.uiState.value.isSavedSuccessfully)
        assertFalse(viewModel.uiState.value.isEditMode)
    }

    @Test
    fun `toggle edit mode preserves existing values`() = runTest {
        val fakeRepo = object : WeatherGPTRepository by ViewModelsTest.createFakeRepository() {
            override suspend fun getFarmerProfile(): ResultState<FarmerProfile> =
                ResultState.Success(FarmerProfile(fullName = "Test Farmer", crop = "Cotton"))

            override suspend fun saveFarmerProfile(profile: FarmerProfile): ResultState<Unit> =
                ResultState.Success(Unit)
        }

        val viewModel = FarmerProfileViewModel(fakeRepo, locationManager)
        advanceUntilIdle()

        assertEquals("Test Farmer", viewModel.uiState.value.fullName)
        assertEquals("Cotton", viewModel.uiState.value.cropName)
        assertFalse(viewModel.uiState.value.isEditMode)

        viewModel.setEditMode(true)
        assertTrue(viewModel.uiState.value.isEditMode)
        assertEquals("Test Farmer", viewModel.uiState.value.fullName)
        assertEquals("Cotton", viewModel.uiState.value.cropName)

        viewModel.setEditMode(false)
        assertFalse(viewModel.uiState.value.isEditMode)
        assertEquals("Test Farmer", viewModel.uiState.value.fullName)
    }
}
