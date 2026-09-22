import { apiRequest } from "./client";
import { WeatherObservation } from "@/types/api";

export async function fetchCurrentWeather(
  lat: number,
  lon: number
): Promise<WeatherObservation> {
  return apiRequest<WeatherObservation>(`/weather/current?lat=${lat}&lon=${lon}`, {
    cacheKey: `weather_${lat.toFixed(2)}_${lon.toFixed(2)}`,
    timeoutMs: 6000,
  });
}

export async function fetchWeatherForecast(
  lat: number,
  lon: number,
  days: number = 3
): Promise<any> {
  return apiRequest<any>(`/weather/forecast?lat=${lat}&lon=${lon}&days=${days}&hourly=true`, {
    cacheKey: `forecast_${lat.toFixed(2)}_${lon.toFixed(2)}`,
    timeoutMs: 6000,
  });
}

export async function fetchWeatherWarnings(
  lat: number,
  lon: number
): Promise<any> {
  return apiRequest<any>(`/weather/warnings?lat=${lat}&lon=${lon}`, {
    cacheKey: `warnings_${lat.toFixed(2)}_${lon.toFixed(2)}`,
    timeoutMs: 6000,
  });
}
