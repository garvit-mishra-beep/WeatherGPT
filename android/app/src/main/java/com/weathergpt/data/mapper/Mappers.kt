package com.weathergpt.data.mapper

import com.weathergpt.data.remote.dto.chat.ChatResponseDto
import com.weathergpt.data.remote.dto.farmer.IrrigationAdvisoryResponseDto
import com.weathergpt.data.remote.dto.farmer.SprayWindowResponseDto
import com.weathergpt.data.remote.dto.gis.BoundaryResponseDto
import com.weathergpt.data.remote.dto.gis.BoundaryUnitDto
import com.weathergpt.data.remote.dto.gis.GISAnalysisResponseDto
import com.weathergpt.data.remote.dto.gis.GeoJsonFeatureCollectionDto
import com.weathergpt.data.remote.dto.gis.GeoJsonFeatureDto
import com.weathergpt.data.remote.dto.gis.GeoJsonGeometryDto
import com.weathergpt.data.remote.dto.gis.HazardIntersectionResponseDto
import com.weathergpt.data.remote.dto.gis.LocationResolutionResponseDto
import com.weathergpt.data.remote.dto.gis.RiskAssessmentResponseDto
import com.weathergpt.data.remote.dto.map.LegendItemDto
import com.weathergpt.data.remote.dto.map.MapLayerDto
import com.weathergpt.data.remote.dto.map.MapSpecificationDto
import com.weathergpt.data.remote.dto.map.MapStyleDto
import com.weathergpt.data.remote.dto.nwp.GFSGridPointResponseDto
import com.weathergpt.data.remote.dto.nwp.NWPModelComparisonResponseDto
import com.weathergpt.data.remote.dto.system.HealthResponseDto
import com.weathergpt.data.remote.dto.system.ReadyResponseDto
import com.weathergpt.data.remote.dto.weather.CurrentWeatherResponseDto
import com.weathergpt.data.remote.dto.weather.DailyForecastDto
import com.weathergpt.data.remote.dto.weather.HourlyForecastDto
import com.weathergpt.data.remote.dto.weather.LocationCoordDto
import com.weathergpt.data.remote.dto.weather.OfficialAlertItemDto
import com.weathergpt.data.remote.dto.weather.WeatherAlertsResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherForecastResponseDto
import com.weathergpt.data.remote.dto.weather.WeatherIntelligenceResponseDto
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.model.ReadinessStatus
import com.weathergpt.domain.model.chat.AdvisoryRecommendation
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.domain.model.chat.ConfidenceAssessment
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.domain.model.chat.EvidenceCitation
import com.weathergpt.domain.model.chat.OfficialWarningCard
import com.weathergpt.domain.model.chat.VisualizationCard
import com.weathergpt.domain.model.farmer.CropWaterBalanceMetrics
import com.weathergpt.domain.model.farmer.IrrigationAdvisory
import com.weathergpt.domain.model.farmer.SpraySuitability
import com.weathergpt.domain.model.gis.AdministrativeBoundary
import com.weathergpt.domain.model.gis.AffectedBoundary
import com.weathergpt.domain.model.gis.BoundaryUnit
import com.weathergpt.domain.model.gis.GISAnalysisReport
import com.weathergpt.domain.model.gis.GeoJsonFeature
import com.weathergpt.domain.model.gis.GeoJsonFeatureCollection
import com.weathergpt.domain.model.gis.GeoJsonGeometry
import com.weathergpt.domain.model.gis.HazardIntersection
import com.weathergpt.domain.model.gis.LocationHierarchy
import com.weathergpt.domain.model.gis.OperationalRisk
import com.weathergpt.domain.model.map.LegendItem
import com.weathergpt.domain.model.map.MapLayer
import com.weathergpt.domain.model.map.MapSpecification
import com.weathergpt.domain.model.map.MapStyle
import com.weathergpt.domain.model.map.MapViewport
import com.weathergpt.domain.model.nwp.DivergenceAnalysis
import com.weathergpt.domain.model.nwp.NWPGridPoint
import com.weathergpt.domain.model.nwp.NWPModelComparison
import com.weathergpt.domain.model.weather.CurrentWeather
import com.weathergpt.domain.model.weather.DailyForecast
import com.weathergpt.domain.model.weather.HourlyForecast
import com.weathergpt.domain.model.weather.LocationCoordinates
import com.weathergpt.domain.model.weather.OfficialAlert
import com.weathergpt.domain.model.weather.WeatherAlertsReport
import com.weathergpt.domain.model.weather.WeatherForecast
import com.weathergpt.domain.model.weather.WeatherIntelligence
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonPrimitive

/**
 * Pure, explicit mapping functions converting Data Transfer Objects (DTOs) into
 * clean Domain Models.
 */
object Mappers {

    // ========================================================================
    // System Mappings
    // ========================================================================

    fun HealthResponseDto.toDomain(): HealthStatus = HealthStatus(
        status = status,
        appName = appName ?: "WeatherGPT",
        environment = environment ?: "production",
        version = version ?: "v1",
        apiVersion = version ?: "v1",
        timestamp = timestamp ?: ""
    )

    fun ReadyResponseDto.toDomain(): ReadinessStatus = ReadinessStatus(
        status = status,
        isReady = ready,
        environment = environment ?: "production",
        apiVersion = apiVersion ?: "v1",
        dependencies = dependencies?.mapValues { it.value.status } ?: emptyMap(),
        timestamp = timestamp ?: ""
    )

    // ========================================================================
    // Chat Mappings
    // ========================================================================

    fun ChatResponseDto.toDomain(): ChatResponse = ChatResponse(
        responseId = responseId,
        sessionId = sessionId,
        brain = DomainBrain.fromValue(brain),
        language = language,
        createdAt = createdAt,
        summary = summary,
        answer = answer,
        data = data,
        recommendation = recommendation?.let {
            AdvisoryRecommendation(
                primaryAction = it.primaryAction,
                urgency = it.urgency,
                actions = it.actions
            )
        },
        alert = alert?.let {
            OfficialWarningCard(
                source = it.source,
                level = it.level,
                hazardType = it.hazardType,
                headline = it.headline,
                description = it.description,
                validUntil = it.validUntil
            )
        },
        visualizations = visualizations.map {
            VisualizationCard(
                type = it.type,
                id = it.id,
                title = it.title,
                chartType = it.chartType,
                spec = it.spec
            )
        },
        sources = sources.map {
            EvidenceCitation(
                authority = it.authority,
                dataset = it.dataset,
                retrievedAt = it.retrievedAt,
                isOfficial = it.isOfficial
            )
        },
        confidence = confidence?.let {
            ConfidenceAssessment(
                evidenceLevel = it.evidenceLevel,
                modelAgreement = it.modelAgreement,
                dataFreshnessStatus = it.dataFreshnessStatus,
                notes = it.notes
            )
        },
        limitations = limitations
    )

    // ========================================================================
    // Weather Mappings
    // ========================================================================

    fun LocationCoordDto.toDomain(): LocationCoordinates = LocationCoordinates(
        latitude = latitude,
        longitude = longitude
    )

    fun CurrentWeatherResponseDto.toDomain(): CurrentWeather = CurrentWeather(
        location = location.toDomain(),
        observationTime = observationTime,
        temperatureC = temperatureC,
        feelsLikeC = feelsLikeC,
        relativeHumidityPct = relativeHumidityPct,
        precipitationMm = precipitationMm,
        rainIntensityCategory = rainIntensityCategory,
        windSpeedKmh = windSpeedKmh,
        windDirectionDeg = windDirectionDeg,
        surfacePressureHpa = surfacePressureHpa,
        weatherCondition = weatherCondition,
        provider = provenance?.provider,
        authority = provenance?.authority
    )

    fun DailyForecastDto.toDomain(): DailyForecast = DailyForecast(
        date = date,
        tempMaxC = tempMaxC,
        tempMinC = tempMinC,
        precipitationSumMm = precipitationSumMm,
        precipitationProbabilityPct = precipitationProbabilityPct,
        windSpeedMaxKmh = windSpeedMaxKmh,
        dominantCondition = dominantCondition,
        tempAvgC = tempAvgC,
        feelsLikeC = feelsLikeC,
        windGustKmh = windGustKmh,
        windDirectionDeg = windDirectionDeg,
        humidityPct = humidityPct,
        weatherCode = weatherCode,
        source = source,
        retrievedAt = retrievedAt,
        forecastValidFrom = forecastValidFrom,
        forecastValidUntil = forecastValidUntil
    )

    fun HourlyForecastDto.toDomain(): HourlyForecast = HourlyForecast(
        time = time,
        temperatureC = temperatureC,
        relativeHumidityPct = relativeHumidityPct,
        precipitationMm = precipitationMm,
        precipitationProbabilityPct = precipitationProbabilityPct,
        windSpeedKmh = windSpeedKmh,
        condition = condition
    )

    fun WeatherForecastResponseDto.toDomain(): WeatherForecast = WeatherForecast(
        location = location.toDomain(),
        generatedAt = generatedAt,
        forecastStart = forecastStart,
        forecastEnd = forecastEnd,
        dailyForecast = dailyForecast.map { dto ->
            val domain = dto.toDomain()
            if (domain.source == null || domain.retrievedAt == null) {
                domain.copy(
                    source = domain.source ?: provenance?.provider ?: "Open-Meteo",
                    retrievedAt = domain.retrievedAt ?: provenance?.retrievalTimestamp ?: generatedAt,
                    forecastValidFrom = domain.forecastValidFrom ?: forecastStart,
                    forecastValidUntil = domain.forecastValidUntil ?: forecastEnd
                )
            } else {
                domain
            }
        },
        hourlyForecast = hourlyForecast?.map { it.toDomain() },
        provider = provenance?.provider,
        retrievedAt = provenance?.retrievalTimestamp ?: generatedAt
    )

    fun OfficialAlertItemDto.toDomain(): OfficialAlert = OfficialAlert(
        alertId = alertId,
        warningColor = warningColor,
        hazard = hazard,
        severity = severity,
        areaDescription = areaDescription,
        headline = headline,
        description = description,
        effectiveFrom = effectiveFrom,
        expiresAt = expiresAt,
        instructions = instructions
    )

    fun WeatherAlertsResponseDto.toDomain(): WeatherAlertsReport = WeatherAlertsReport(
        authority = authority,
        retrievedAt = retrievedAt,
        activeAlertsCount = activeAlertsCount,
        alerts = alerts.map { it.toDomain() }
    )

    fun WeatherIntelligenceResponseDto.toDomain(): WeatherIntelligence = WeatherIntelligence(
        latitude = latitude,
        longitude = longitude,
        dataQuality = dataQuality,
        currentObservation = currentObservation?.toDomain(),
        alerts = alerts?.map { it.toDomain() } ?: emptyList(),
        rawProvenance = provenance
    )

    // ========================================================================
    // Farmer Mappings
    // ========================================================================

    fun IrrigationAdvisoryResponseDto.toDomain(): IrrigationAdvisory = IrrigationAdvisory(
        action = action,
        urgency = urgency,
        metrics = CropWaterBalanceMetrics(
            referenceEt0MmDay = metrics.referenceEt0MmDay,
            cropKc = metrics.cropKc,
            dailyWaterDemandMm = metrics.dailyWaterDemandMm,
            forecastRainfall48hMm = metrics.forecastRainfall48hMm,
            netDeficitMm = metrics.netDeficitMm,
            finalDepletionMm = metrics.finalDepletionMm
        ),
        rationale = rationale,
        calculationMethod = provenance?.calculationMethod ?: "FAO-56 Penman-Monteith"
    )

    fun SprayWindowResponseDto.toDomain(): SpraySuitability = SpraySuitability(
        isSuitable = isSuitable,
        conditionLevel = conditionLevel,
        recommendation = recommendation,
        windSuitable = windSuitable,
        rainProbabilitySuitable = rainProbabilitySuitable,
        calculationMethod = provenance?.calculationMethod ?: "Deterministic Agronomic Spray Matrix"
    )

    // ========================================================================
    // GIS & GeoJSON Mappings
    // ========================================================================

    fun BoundaryUnitDto.toDomain(): BoundaryUnit = BoundaryUnit(
        code = code,
        name = name,
        level = level,
        parentCode = parentCode,
        areaSqkm = areaSqkm
    )

    fun LocationResolutionResponseDto.toDomain(): LocationHierarchy = LocationHierarchy(
        latitude = latitude,
        longitude = longitude,
        isResolved = isResolved,
        country = country?.toDomain(),
        state = state?.toDomain(),
        district = district?.toDomain(),
        subdistrict = subdistrict?.toDomain()
    )

    fun BoundaryResponseDto.toDomain(): AdministrativeBoundary = AdministrativeBoundary(
        code = code,
        name = name,
        level = level,
        parentCode = parentCode,
        areaSqkm = areaSqkm,
        rawGeoJson = geojson
    )

    fun HazardIntersectionResponseDto.toDomain(): HazardIntersection = HazardIntersection(
        alertId = alertId,
        event = event,
        severity = severity,
        totalAffectedBoundaries = totalAffectedBoundaries,
        totalAffectedAreaSqkm = totalAffectedAreaSqkm,
        affectedUnits = affectedUnits.map {
            AffectedBoundary(
                boundary = it.boundary?.toDomain(),
                exposedAreaSqkm = it.exposedAreaSqkm,
                exposedAreaPct = it.exposedAreaPct
            )
        }
    )

    fun RiskAssessmentResponseDto.toDomain(): OperationalRisk = OperationalRisk(
        district = district,
        hazardType = hazardType,
        hazardIndex = hazardIndex,
        exposureIndex = exposureIndex,
        vulnerabilityIndex = vulnerabilityIndex,
        compositeRiskScore = compositeRiskScore,
        riskLevel = riskLevel,
        actionPriority = actionPriority
    )

    fun GISAnalysisResponseDto.toDomain(): GISAnalysisReport = GISAnalysisReport(
        analysisId = analysisId,
        latitude = latitude,
        longitude = longitude,
        hazardScore = hazardScore,
        exposureScore = exposureScore,
        vulnerabilityScore = vulnerabilityScore,
        impactScore = impactScore,
        riskCategory = riskCategory,
        actionableGuidance = actionableGuidance
    )

    fun GeoJsonGeometryDto.toDomain(): GeoJsonGeometry {
        val coords = coordinates
        return when (type.lowercase()) {
            "point" -> {
                if (coords is JsonArray && coords.size >= 2) {
                    val lon = (coords[0] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                    val lat = (coords[1] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                    GeoJsonGeometry.Point(longitude = lon, latitude = lat)
                } else GeoJsonGeometry.Unknown(type)
            }
            "polygon" -> {
                if (coords is JsonArray) {
                    val rings = mutableListOf<List<Pair<Double, Double>>>()
                    coords.forEach { ringElem ->
                        if (ringElem is JsonArray) {
                            val ringCoords = mutableListOf<Pair<Double, Double>>()
                            ringElem.forEach { ptElem ->
                                if (ptElem is JsonArray && ptElem.size >= 2) {
                                    val lon = (ptElem[0] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                                    val lat = (ptElem[1] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                                    ringCoords.add(Pair(lon, lat))
                                }
                            }
                            rings.add(ringCoords)
                        }
                    }
                    GeoJsonGeometry.Polygon(rings = rings)
                } else GeoJsonGeometry.Unknown(type)
            }
            "multipolygon" -> {
                if (coords is JsonArray) {
                    val polygons = mutableListOf<List<List<Pair<Double, Double>>>>()
                    coords.forEach { polyElem ->
                        if (polyElem is JsonArray) {
                            val rings = mutableListOf<List<Pair<Double, Double>>>()
                            polyElem.forEach { ringElem ->
                                if (ringElem is JsonArray) {
                                    val ringCoords = mutableListOf<Pair<Double, Double>>()
                                    ringElem.forEach { ptElem ->
                                        if (ptElem is JsonArray && ptElem.size >= 2) {
                                            val lon = (ptElem[0] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                                            val lat = (ptElem[1] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                                            ringCoords.add(Pair(lon, lat))
                                        }
                                    }
                                    rings.add(ringCoords)
                                }
                            }
                            polygons.add(rings)
                        }
                    }
                    GeoJsonGeometry.MultiPolygon(polygons = polygons)
                } else GeoJsonGeometry.Unknown(type)
            }
            "linestring" -> {
                if (coords is JsonArray) {
                    val pts = mutableListOf<Pair<Double, Double>>()
                    coords.forEach { ptElem ->
                        if (ptElem is JsonArray && ptElem.size >= 2) {
                            val lon = (ptElem[0] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                            val lat = (ptElem[1] as? JsonPrimitive)?.content?.toDoubleOrNull() ?: 0.0
                            pts.add(Pair(lon, lat))
                        }
                    }
                    GeoJsonGeometry.LineString(coordinates = pts)
                } else GeoJsonGeometry.Unknown(type)
            }
            else -> GeoJsonGeometry.Unknown(type)
        }
    }

    fun GeoJsonFeatureDto.toDomain(): GeoJsonFeature = GeoJsonFeature(
        id = id,
        geometry = geometry?.toDomain(),
        properties = properties?.mapValues { (_, v) ->
            if (v is JsonPrimitive) v.content else v.toString()
        } ?: emptyMap(),
        bbox = bbox
    )

    fun GeoJsonFeatureCollectionDto.toDomain(): GeoJsonFeatureCollection = GeoJsonFeatureCollection(
        features = features.map { it.toDomain() },
        bbox = bbox
    )

    // ========================================================================
    // NWP Mappings
    // ========================================================================

    fun GFSGridPointResponseDto.toDomain(): NWPGridPoint = NWPGridPoint(
        model = model,
        gridResolutionDeg = gridResolutionDeg,
        latitude = location.latitude,
        longitude = location.longitude,
        forecastLeadHours = forecastLeadHours,
        validTime = validTime,
        temperature2mC = atmosphericVariables.temperature2mC,
        relativeHumidity2mPct = atmosphericVariables.relativeHumidity2mPct,
        accumulatedPrecipMm = atmosphericVariables.accumulatedPrecipMm,
        windSpeedKmh = atmosphericVariables.windSpeedKmh,
        windDirectionDeg = atmosphericVariables.windDirectionDeg,
        windGustKmh = atmosphericVariables.windGustKmh,
        pressureMslHpa = atmosphericVariables.pressureMslHpa,
        totalCloudCoverPct = atmosphericVariables.totalCloudCoverPct,
        capeJkg = atmosphericVariables.capeJkg,
        status = "AVAILABLE"
    )

    fun com.weathergpt.data.remote.dto.nwp.WRFGridPointResponseDto.toDomain(): NWPGridPoint = NWPGridPoint(
        model = model,
        gridResolutionDeg = gridResolutionDeg,
        latitude = location.latitude,
        longitude = location.longitude,
        forecastLeadHours = forecastLeadHours,
        validTime = validTime ?: "",
        temperature2mC = atmosphericVariables?.temperature2mC ?: 0.0,
        relativeHumidity2mPct = atmosphericVariables?.relativeHumidity2mPct ?: 0.0,
        accumulatedPrecipMm = atmosphericVariables?.accumulatedPrecipMm ?: 0.0,
        windSpeedKmh = atmosphericVariables?.windSpeedKmh ?: 0.0,
        windDirectionDeg = atmosphericVariables?.windDirectionDeg ?: 0.0,
        windGustKmh = atmosphericVariables?.windGustKmh,
        pressureMslHpa = atmosphericVariables?.pressureMslHpa ?: 1013.25,
        totalCloudCoverPct = atmosphericVariables?.totalCloudCoverPct ?: 0.0,
        capeJkg = atmosphericVariables?.capeJkg,
        status = status,
        statusMessage = message
    )

    fun NWPModelComparisonResponseDto.toDomain(): NWPModelComparison = NWPModelComparison(
        latitude = latitude,
        longitude = longitude,
        forecastLeadHours = forecastLeadHours,
        modelsStatus = modelsStatus,
        models = models,
        variablesCompared = variablesCompared.map {
            com.weathergpt.domain.model.nwp.VariableComparison(
                variable = it.variable,
                units = it.units,
                gfs = it.gfs,
                ecmwf = it.ecmwf,
                wrf = it.wrf,
                absoluteDiff = it.absoluteDiff
            )
        },
        divergenceAnalysis = divergenceAnalysis?.let {
            DivergenceAnalysis(
                variable = it.variable,
                units = it.units,
                modelsCompared = it.modelsCompared,
                meanForecast = it.meanForecast,
                stdDev = it.stdDev,
                divergenceRatio = it.divergenceRatio,
                agreementCategory = it.agreementCategory,
                isActionable = it.isActionable
            )
        },
        wrfStatus = modelsStatus["WRF_REGIONAL"] ?: "UNAVAILABLE"
    )

    // ========================================================================
    // Map Mappings
    // ========================================================================

    fun MapStyleDto.toDomain(): MapStyle = MapStyle(
        fillColor = fillColor,
        fillOpacity = fillOpacity,
        strokeColor = strokeColor,
        strokeWidth = strokeWidth,
        pointRadius = pointRadius,
        iconName = iconName
    )

    fun MapLayerDto.toDomain(): MapLayer = MapLayer(
        id = id,
        name = name ?: title ?: id,
        type = type,
        sourceId = sourceId,
        sourceData = (sourceData ?: geojson)?.toDomain(),
        paint = paint?.mapValues { (_, v) ->
            if (v is JsonPrimitive) v.content else v.toString()
        } ?: emptyMap(),
        style = style?.toDomain(),
        visible = visible
    )

    fun LegendItemDto.toDomain(): LegendItem = LegendItem(
        label = label,
        color = color,
        valueRange = valueRange,
        description = description,
        hazardType = hazardType,
        officialLevel = officialLevel
    )

    fun MapSpecificationDto.toDomain(): MapSpecification {
        val resolvedId = id ?: mapId ?: "map_default"
        val centerLon = viewport?.center?.getOrNull(0) ?: center?.getOrNull(0) ?: 78.9629
        val centerLat = viewport?.center?.getOrNull(1) ?: center?.getOrNull(1) ?: 20.5937
        val resolvedZoom = viewport?.zoom ?: zoom ?: 8.5
        val resolvedBbox = viewport?.bbox ?: bbox

        val vp = MapViewport(
            centerLongitude = centerLon,
            centerLatitude = centerLat,
            zoom = resolvedZoom,
            pitch = viewport?.pitch ?: 0.0,
            bearing = viewport?.bearing ?: 0.0,
            bbox = resolvedBbox
        )

        return MapSpecification(
            id = resolvedId,
            title = title,
            viewport = vp,
            layers = layers.map { it.toDomain() },
            legend = legend.map { it.toDomain() },
            provenance = provenance?.mapValues { (_, v) ->
                if (v is JsonPrimitive) v.content else v.toString()
            } ?: emptyMap(),
            quality = quality
        )
    }

    // ========================================================================
    // 8. Vayubodhak Decision Intelligence (NirnayCard & ActionWindow Phase 2)
    // ========================================================================

    fun com.weathergpt.data.remote.dto.decision.CandidateHourEvaluationDto.toDomain(): com.weathergpt.domain.model.decision.CandidateHourEvaluation =
        com.weathergpt.domain.model.decision.CandidateHourEvaluation(
            timeIso = timeIso,
            windSpeedKmh = windSpeedKmh,
            rainProbabilityPct = rainProbabilityPct,
            precipitationMm = precipitationMm,
            temperatureC = temperatureC,
            passed = passed,
            failedReasons = failedReasons
        )

    fun com.weathergpt.data.remote.dto.decision.ActionWindowPeriodDto.toDomain(): com.weathergpt.domain.model.decision.ActionWindowPeriod =
        com.weathergpt.domain.model.decision.ActionWindowPeriod(
            windowId = windowId,
            startTimeIso = startTimeIso,
            endTimeIso = endTimeIso,
            durationHours = durationHours,
            score = score,
            avgWindSpeedKmh = avgWindSpeedKmh,
            maxWindSpeedKmh = maxWindSpeedKmh,
            maxRainProbabilityPct = maxRainProbabilityPct,
            totalRainfallMm = totalRainfallMm,
            summary = summary,
            recommended = recommended
        )

    fun com.weathergpt.data.remote.dto.decision.ActionWindowDto.toDomain(): com.weathergpt.domain.model.decision.ActionWindow =
        com.weathergpt.domain.model.decision.ActionWindow(
            status = status,
            isAvailable = status.equals("available", ignoreCase = true),
            bestWindow = bestWindow?.toDomain(),
            fallbackWindows = fallbackWindows.map { it.toDomain() },
            score = score,
            constraints = constraints?.mapValues { (_, v) ->
                if (v is JsonPrimitive) v.content else v.toString()
            } ?: emptyMap(),
            confidence = com.weathergpt.domain.model.decision.DecisionConfidence.fromRaw(confidence ?: "high"),
            reason = reason,
            hourlyEvaluations = hourlyEvaluations?.map { it.toDomain() }
        )

    fun com.weathergpt.data.remote.dto.decision.LedgerRuleEvaluationDto.toDomain(): com.weathergpt.domain.model.decision.LedgerRuleEvaluation =
        com.weathergpt.domain.model.decision.LedgerRuleEvaluation(
            ruleName = ruleName,
            threshold = threshold?.let { if (it is JsonPrimitive) it.content else it.toString() } ?: "",
            observedValue = observedValue?.let { if (it is JsonPrimitive) it.content else it.toString() } ?: "",
            unit = unit,
            operator = operator,
            satisfied = satisfied,
            rationale = rationale
        )

    fun com.weathergpt.data.remote.dto.decision.EvidenceLedgerDto.toDomain(): com.weathergpt.domain.model.decision.EvidenceLedger =
        com.weathergpt.domain.model.decision.EvidenceLedger(
            decisionId = decisionId,
            timestamp = timestamp,
            question = question,
            rules = rules.map { it.toDomain() },
            inputs = inputs?.mapValues { (_, v) ->
                if (v is JsonPrimitive) v.content else v.toString()
            } ?: emptyMap(),
            sources = sources?.map { it.toString() } ?: emptyList()
        )

    fun com.weathergpt.data.remote.dto.decision.NirnayCardDto.toDomain(): com.weathergpt.domain.model.decision.NirnayCard {
        val uncGfs = uncertainty?.get("gfs_confidence")?.let { if (it is JsonPrimitive) it.content else it.toString() } ?: "high"
        val uncWrf = uncertainty?.get("wrf_status")?.let { if (it is JsonPrimitive) it.content else it.toString() } ?: "unavailable"
        val uncNote = uncertainty?.get("statement")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: uncertainty?.get("uncertainty_note")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: "Guidance based on numerical forecast; independent WRF comparison is unavailable"
        val uncLead = uncertainty?.get("lead_time_hours")?.let {
            if (it is JsonPrimitive) it.content.toDoubleOrNull() else null
        }

        val riskStr = impact?.get("primary_risk")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("operational_risk")?.let { if (it is JsonPrimitive) it.content else it.toString() }
        val lossStr = impact?.get("loss_potential")?.let { if (it is JsonPrimitive) it.content else it.toString() }

        val evidenceMap = evidence?.mapValues { (_, v) ->
            if (v is JsonPrimitive) v.content else v.toString()
        } ?: emptyMap()

        // Phase 3 Alert-to-Impact Intelligence extraction
        val alertId = evidence?.get("primary_alert_id")?.let { if (it is JsonPrimitive) it.content else it.toString() }
        val hazard = evidence?.get("hazard_type")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("hazard")?.let { if (it is JsonPrimitive) it.content else it.toString() }
        val issuingOffice = evidence?.get("issuing_office")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("issuing_office")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: evidenceMap["sources"]?.split(",")?.firstOrNull()?.trim()?.removePrefix("[")?.removeSuffix("]")?.replace("\"", "")
        val isOfficial = evidence?.get("is_official")?.let {
            if (it is JsonPrimitive) it.booleanOrNull ?: true else true
        } ?: true
        val alertSeverity = evidence?.get("primary_warning_level")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: severity

        val rawExp = evidence?.get("exposure_state")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("exposure_state")?.let { if (it is JsonPrimitive) it.content else it.toString() }
        val affectedAreaStatus = com.weathergpt.domain.model.decision.ExposureState.fromRaw(rawExp)

        val affectedAreaName = evidence?.get("affected_area_name")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("affected_area_name")?.let { if (it is JsonPrimitive) it.content else it.toString() }

        val exposureStatus = if (rawExp == null || rawExp.equals("UNKNOWN", ignoreCase = true) || rawExp.equals("NONE", ignoreCase = true)) {
            "UNAVAILABLE"
        } else {
            "AVAILABLE"
        }

        val exposureSummary = when (affectedAreaStatus) {
            com.weathergpt.domain.model.decision.ExposureState.INSIDE -> "Directly inside active warning area"
            com.weathergpt.domain.model.decision.ExposureState.BUFFER -> "Near warning boundary (within 25 km buffer)"
            com.weathergpt.domain.model.decision.ExposureState.OUTSIDE -> "Outside active warning area"
            com.weathergpt.domain.model.decision.ExposureState.UNKNOWN -> "Affected area could not be verified"
        }

        val exposedAreaSqkm = impact?.get("exposed_area_sqkm")?.let {
            if (it is JsonPrimitive) it.doubleOrNull else null
        }

        val compositeImpactScore = evidence?.get("composite_impact_score")?.let {
            if (it is JsonPrimitive) it.doubleOrNull else null
        } ?: impact?.get("composite_impact_score")?.let {
            if (it is JsonPrimitive) it.content.replace("/10.0", "").toDoubleOrNull() else null
        }

        val riskCategory = impact?.get("risk_category")?.let { if (it is JsonPrimitive) it.content else it.toString() }
            ?: impact?.get("risk_tier")?.let { if (it is JsonPrimitive) it.content else it.toString() }

        val hasAlert = !alertId.isNullOrBlank() || !hazard.isNullOrBlank() || (rawExp != null && !rawExp.equals("NONE", ignoreCase = true))

        val alertImpactInfo = if (hasAlert) {
            com.weathergpt.domain.model.decision.AlertImpactInfo(
                alertId = alertId,
                hazard = hazard,
                issuingOffice = issuingOffice,
                isOfficial = isOfficial,
                alertSeverity = alertSeverity,
                affectedAreaStatus = affectedAreaStatus,
                affectedAreaName = affectedAreaName,
                exposureStatus = exposureStatus,
                exposureSummary = exposureSummary,
                exposedAreaSqkm = exposedAreaSqkm,
                potentialImpact = riskStr ?: lossStr,
                compositeImpactScore = compositeImpactScore,
                riskCategory = riskCategory
            )
        } else {
            null
        }

        val parsedUncertainty = com.weathergpt.domain.model.decision.DecisionUncertainty(
            gfsConfidence = uncGfs,
            wrfStatus = uncWrf,
            uncertaintyNote = uncNote,
            leadTimeHours = uncLead,
            exposureDataAvailable = (exposureStatus != "UNAVAILABLE")
        )

        return com.weathergpt.domain.model.decision.NirnayCard(
            question = question,
            verdict = com.weathergpt.domain.model.decision.DecisionVerdict.fromRaw(verdict),
            severity = com.weathergpt.domain.model.decision.DecisionSeverity.fromRaw(severity),
            recommendedAction = recommendedAction,
            actionWindow = actionWindow.toDomain(),
            confidence = com.weathergpt.domain.model.decision.DecisionConfidence.fromRaw(confidence),
            uncertainty = parsedUncertainty,
            why = why,
            primaryRisk = riskStr,
            lossPotential = lossStr,
            alternatives = alternatives,
            evidenceMetrics = evidenceMap,
            ledger = ledger?.toDomain(),
            alertImpact = alertImpactInfo,
            explanation = explanation
        )
    }
}
