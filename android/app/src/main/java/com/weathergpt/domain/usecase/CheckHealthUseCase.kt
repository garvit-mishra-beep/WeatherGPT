package com.weathergpt.domain.usecase

import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus
import com.weathergpt.domain.model.ReadinessStatus
import com.weathergpt.domain.repository.WeatherGPTRepository

/**
 * UseCase to verify liveness connectivity with the WeatherGPT backend.
 */
class CheckHealthUseCase(
    private val repository: WeatherGPTRepository
) {
    suspend operator fun invoke(): ResultState<HealthStatus> {
        return repository.checkHealth()
    }
}

/**
 * UseCase to verify backend dependency readiness.
 */
class CheckReadinessUseCase(
    private val repository: WeatherGPTRepository
) {
    suspend operator fun invoke(): ResultState<ReadinessStatus> {
        return repository.checkReadiness()
    }
}
