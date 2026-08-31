package com.weathergpt.data.remote

import com.weathergpt.data.remote.dto.chat.ChatRequestDto
import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryRequestDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryResponseDto
import com.weathergpt.data.remote.dto.farmer.SprayWindowRequestDto
import com.weathergpt.data.remote.dto.farmer.SprayWindowResponseDto
import com.weathergpt.data.remote.dto.gis.BoundaryResponseDto
import com.weathergpt.data.remote.dto.gis.GISAnalysisRequestDto
import com.weathergpt.data.remote.dto.gis.GISAnalysisResponseDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionRequestDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionResponseDto
import com.weathergpt.data.remote.dto.gis.LocationResolutionResponseDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentRequestDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentResponseDto
import com.weathergpt.data.remote.dto.map.MapSpecificationDto
import com.weathergpt.data.remote.dto.map.RiskMapRequestDto
import com.weathergpt.data.remote.dto.map.WarningMapRequestDto
import com.weathergpt.data.remote.dto.nwp.GFSGridPointResponseDto
import com.weathergpt.data.remote.dto.nwp.NWPModelComparisonResponseDto
import com.weathergpt.data.remote.dto.system.HealthResponseDto
import com.weathergpt.data.remote.dto.system.ReadyResponseDto
import com.weathergpt.data.remote.dto.system.RootMetadataDto
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherIntelligenceResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Central Retrofit API service interface for the WeatherGPT FastAPI backend (/api/v1).
 *
 * Implements typed contracts matching docs/32_FASTAPI_API.md across all endpoint groups.
 */
interface WeatherGPTApiService {

    // ========================================================================
    // 1. SYSTEM
    // ========================================================================

    @GET("api/v1/health")
    suspend fun getHealth(): HealthResponseDto

    @GET("api/v1/ready")
    suspend fun getReadiness(): ReadyResponseDto

    @GET("api/v1/")
    suspend fun getRootMetadata(): RootMetadataDto

    // ========================================================================
    // 2. CHAT & LLM ORCHESTRATION
    // ========================================================================

    @POST("api/v1/chat")
    suspend fun sendChatMessage(
        @Body request: ChatRequestDto
    ): ChatResponseDto

    // ========================================================================
    // 3. WEATHER & OFFICIAL ALERTS
    // ========================================================================

    @GET("api/v1/weather/current")
    suspend fun getCurrentWeather(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double
    ): CurrentWeatherResponseDto

    @GET("api/v1/weather/forecast")
    suspend fun getWeatherForecast(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("days") days: Int = 3,
        @Query("hourly") hourly: Boolean = true
    ): WeatherForecastResponseDto

    @GET("api/v1/weather/alerts")
    suspend fun getWeatherAlerts(
        @Query("district") district: String? = null,
        @Query("lat") latitude: Double? = null,
        @Query("lon") longitude: Double? = null
    ): WeatherAlertsResponseDto

    @GET("api/v1/weather/intelligence")
    suspend fun getWeatherIntelligence(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("lead_hours") leadHours: Int = 24,
        @Query("include_nwp") includeNwp: Boolean = true
    ): WeatherIntelligenceResponseDto

    // ========================================================================
    // 4. AGRICULTURAL & FARMER DECISION SUPPORT
    // ========================================================================

    @POST("api/v1/farmer/irrigation-advisory")
    suspend fun getIrrigationAdvisory(
        @Body request: IrrigationAdvisoryRequestDto
    ): IrrigationAdvisoryResponseDto

    @POST("api/v1/farmer/spray-window")
    suspend fun getSprayWindowAdvisory(
        @Body request: SprayWindowRequestDto
    ): SprayWindowResponseDto

    // ========================================================================
    // 5. GIS & SPATIAL INTELLIGENCE
    // ========================================================================

    @GET("api/v1/gis/location")
    suspend fun getLocationHierarchy(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double
    ): LocationResolutionResponseDto

    @GET("api/v1/gis/boundary/{level}/{code}")
    suspend fun getBoundary(
        @Path("level") level: String,
        @Path("code") code: String
    ): BoundaryResponseDto

    @POST("api/v1/gis/hazard-intersection")
    suspend fun getHazardIntersection(
        @Body request: HazardIntersectionRequestDto
    ): HazardIntersectionResponseDto

    @POST("api/v1/gis/risk-assessment")
    suspend fun getRiskAssessment(
        @Body request: RiskAssessmentRequestDto
    ): RiskAssessmentResponseDto

    @POST("api/v1/gis/analysis")
    suspend fun getGISAnalysis(
        @Body request: GISAnalysisRequestDto
    ): GISAnalysisResponseDto

    // ========================================================================
    // 6. NWP NUMERICAL WEATHER PREDICTION
    // ========================================================================

    @GET("api/v1/nwp/gfs")
    suspend fun getGFSGridPoint(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("lead_hours") leadHours: Int = 24
    ): GFSGridPointResponseDto

    @GET("api/v1/nwp/wrf")
    suspend fun getWRFGridPoint(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("lead_hours") leadHours: Int = 24
    ): com.weathergpt.data.remote.dto.nwp.WRFGridPointResponseDto

    @GET("api/v1/nwp/comparison")
    suspend fun getNWPModelComparison(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("lead_hours") leadHours: Int = 24
    ): NWPModelComparisonResponseDto

    // ========================================================================
    // 7. MAP-READY DATA & DECLARATIVE MAP SPECS
    // ========================================================================

    @GET("api/v1/map/point")
    suspend fun getPointWeatherMap(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double
    ): MapSpecificationDto

    @POST("api/v1/map/warning")
    suspend fun getWarningMap(
        @Body request: WarningMapRequestDto
    ): MapSpecificationDto

    @POST("api/v1/map/risk")
    suspend fun getRiskMap(
        @Body request: RiskMapRequestDto
    ): MapSpecificationDto
}
