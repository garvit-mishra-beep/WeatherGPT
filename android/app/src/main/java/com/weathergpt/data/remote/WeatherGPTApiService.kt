package com.weathergpt.data.remote

import com.weathergpt.data.remote.dto.chat.ChatRequestDto
import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import com.weathergpt.data.remote.dto.climate.ClimateNormalsResponseDto
import com.weathergpt.data.remote.dto.climate.ClimateTrendsResponseDto
import com.weathergpt.data.remote.dto.decision.DecisionRequestDto
import com.weathergpt.data.remote.dto.decision.NirnayCardDto
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
import com.weathergpt.data.remote.dto.voice.VoiceQueryResponseDto
import com.weathergpt.data.remote.dto.voice.VoiceSttResponseDto
import com.weathergpt.data.remote.dto.voice.VoiceTtsRequestDto
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherIntelligenceResponseDto
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

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

    @POST("api/v1/decisions")
    suspend fun evaluateDecision(
        @Body request: DecisionRequestDto
    ): NirnayCardDto

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

    @POST("api/v1/analyst/risk-matrix")
    suspend fun getAnalystRiskMatrix(
        @Body request: RiskAssessmentRequestDto
    ): RiskAssessmentResponseDto

    @POST("api/v1/gis/analysis")
    suspend fun getGISAnalysis(
        @Body request: GISAnalysisRequestDto
    ): GISAnalysisResponseDto

    // ========================================================================
    // 5B. CLIMATE INTELLIGENCE & CLIMATOLOGY
    // ========================================================================

    @GET("api/v1/climate/trends")
    suspend fun getClimateTrends(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("location") location: String? = null,
        @Query("variable") variable: String = "rainfall",
        @Query("start_year") startYear: Int = 1991,
        @Query("end_year") endYear: Int = 2024
    ): ClimateTrendsResponseDto

    @GET("api/v1/climate/normals")
    suspend fun getClimateNormals(
        @Query("lat") latitude: Double,
        @Query("lon") longitude: Double,
        @Query("location") location: String? = null,
        @Query("month") month: Int? = null
    ): ClimateNormalsResponseDto

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

    // ========================================================================
    // 8. VOICE INTERACTION (SPEECH-TO-TEXT & TEXT-TO-SPEECH)
    // ========================================================================

    @Multipart
    @POST("api/v1/voice/stt")
    suspend fun speechToText(
        @Part audio: MultipartBody.Part,
        @Query("language_code") languageCode: String? = null
    ): VoiceSttResponseDto

    @POST("api/v1/voice/tts")
    @Streaming
    suspend fun textToSpeech(
        @Body request: VoiceTtsRequestDto
    ): ResponseBody

    @Multipart
    @POST("api/v1/voice/query")
    suspend fun voiceQuery(
        @Part audio: MultipartBody.Part,
        @Part("language_code") languageCode: RequestBody? = null,
        @Part("session_id") sessionId: RequestBody? = null,
        @Part("latitude") latitude: RequestBody? = null,
        @Part("longitude") longitude: RequestBody? = null,
        @Part("selected_brain") selectedBrain: RequestBody? = null
    ): VoiceQueryResponseDto

    // ========================================================================
    // 9. PROACTIVE DECISIONS & PUSH DEVICE TOKENS
    // ========================================================================

    @POST("api/v1/proactive/devices")
    suspend fun registerDeviceToken(
        @Body request: com.weathergpt.data.remote.dto.proactive.RegisterDeviceRequestDto
    ): com.weathergpt.data.remote.dto.proactive.RegisterDeviceResponseDto

    // ========================================================================
    // 10. OPERATIONAL STREAMING & INCREMENTAL SYNCHRONIZATION
    // ========================================================================

    @GET("api/v1/sync/operational-state")
    suspend fun getOperationalSyncState(
        @Query("cursor_seq") cursorSeq: Int = 0,
        @Query("last_synced_revision") lastSyncedRevision: Int = 0,
        @Query("district") district: String? = null,
        @Query("limit") limit: Int = 50
    ): com.weathergpt.data.remote.dto.sync.OperationalSyncResponseDto
}
