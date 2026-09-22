import { apiRequest } from "./client";
import { DataSourceHealthResponse, DataSourceSummary } from "@/types/api";

export async function fetchDataSources(): Promise<DataSourceSummary[]> {
  return apiRequest<DataSourceSummary[]>("/data-sources", {
    cacheKey: "data_sources_catalog",
    timeoutMs: 6000,
  });
}

export async function fetchDataSourcesHealth(): Promise<DataSourceHealthResponse> {
  return apiRequest<DataSourceHealthResponse>("/data-sources/health", {
    cacheKey: "data_sources_health",
    timeoutMs: 6000,
  });
}

export async function fetchSystemHealth(): Promise<any> {
  return apiRequest<any>("/health", {
    timeoutMs: 4000,
  });
}

export async function fetchSystemReadiness(): Promise<any> {
  return apiRequest<any>("/ready", {
    timeoutMs: 5000,
  });
}
