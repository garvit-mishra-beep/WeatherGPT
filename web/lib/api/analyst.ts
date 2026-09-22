import { apiRequest } from "./client";
import { RiskMatrixResponse } from "@/types/api";

export interface RiskMatrixRequestPayload {
  district_name: string;
  latitude?: number;
  longitude?: number;
  observed_rain_mm?: number;
  observed_wind_kmh?: number;
  observed_temp_c?: number;
  hazard_type?: string;
  precip_24h_percentile?: number;
  exposure_index?: number;
  vulnerability_index?: number;
}

export async function fetchRiskMatrix(
  payload: RiskMatrixRequestPayload
): Promise<RiskMatrixResponse> {
  return apiRequest<RiskMatrixResponse>("/analyst/risk-matrix", {
    method: "POST",
    body: JSON.stringify(payload),
    cacheKey: `risk_matrix_${payload.district_name}`,
    timeoutMs: 8000,
  });
}
