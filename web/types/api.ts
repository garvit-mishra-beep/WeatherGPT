// ==============================================================================
// VAYUBODHAK API CONTRACTS & TYPES
// Fully aligned with backend Pydantic models (FastAPI /api/v1)
// ==============================================================================

export type DecisionVerdict =
  | "GO"
  | "PROCEED_WITH_CAUTION"
  | "POSTPONE"
  | "NO_GO"
  | "MONITOR"
  | "INSUFFICIENT_DATA";

export type DecisionSeverity = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export type SystemOperationalState =
  | "FULL_OPERATIONAL"
  | "DEGRADED_DATA"
  | "OFFLINE"
  | "RECOVERING"
  | "UNAVAILABLE";

export type DataSourceStatus =
  | "LIVE"
  | "CACHED"
  | "FALLBACK"
  | "HISTORICAL"
  | "UNAVAILABLE";

export type LlmStatus = "LLM_AVAILABLE" | "LLM_UNAVAILABLE";

export type BrainType = "GENERAL" | "FARMER" | "RESEARCHER" | "ANALYST";

export interface CandidateHourEvaluation {
  time_iso: string;
  wind_speed_kmh: number;
  rain_probability_pct: number;
  precipitation_mm: number;
  passed: boolean;
  failure_reasons: string[];
}

export interface ActionWindowPeriod {
  start_time_iso: string;
  end_time_iso: string;
  duration_hours: number;
  overall_score: number;
  avg_wind_kmh: number;
  avg_rain_prob_pct: number;
}

export interface ActionWindow {
  status: "available" | "unavailable" | "marginal";
  headline: string;
  best_window?: ActionWindowPeriod | null;
  fallback_windows: ActionWindowPeriod[];
  total_candidate_hours_scanned: number;
  valid_hours_count: number;
  rejection_summary: Record<string, number>;
  hourly_evaluations: CandidateHourEvaluation[];
}

export interface LedgerRuleEvaluation {
  rule_id: string;
  description: string;
  status: "PASSED" | "FAILED" | "MARGINAL";
  threshold: string;
  observed_value: string;
  mandatory: boolean;
}

export interface EvidenceSourceLedger {
  source_id: string;
  authority: string;
  observed_time_iso: string;
  parameter: string;
  value: any;
  confidence: number;
}

export interface NirnayLedger {
  decision_id: string;
  domain: string;
  verdict: DecisionVerdict;
  severity: DecisionSeverity;
  rules_evaluated: LedgerRuleEvaluation[];
  sources: EvidenceSourceLedger[];
  signature: string;
  timestamp_iso: string;
}

export interface NirnayCard {
  decision_id: string;
  verdict: DecisionVerdict;
  severity: DecisionSeverity;
  headline: string;
  recommended_action: string;
  action_window: ActionWindow;
  sourceStatus: string;
  evidence: Record<string, any>;
  uncertainty?: string | null;
  explanation?: string | null;
  explanationLanguage?: string;
  ledger?: NirnayLedger | null;
  timestamp_iso?: string;
}

export interface OperationalEvent {
  event_id: string;
  event_type: string;
  source_id: string;
  source_authority: string;
  source_record_id?: string | null;
  sequence_number?: number | null;
  geography: string;
  details: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface OperationalNotification {
  notification_id: string;
  priority: "OFFICIAL_WARNING" | "DECISION_CHANGE" | "HAZARD_ADVISORY" | "INFO";
  title: string;
  body: string;
  timestamp_iso: string;
  metadata: Record<string, any>;
}

export interface OperationalSyncResponse {
  server_time_iso: string;
  cursor_sequence: number;
  latest_sequence: number;
  latest_revision: number;
  source_status: string;
  events: OperationalEvent[];
  latest_nirnay_card?: NirnayCard | null;
  latest_decision_revision?: Record<string, any> | null;
  has_more: boolean;
}

export interface WeatherObservation {
  location: { latitude: number; longitude: number };
  observation_time: string;
  temperature_c: number;
  feels_like_c: number;
  relative_humidity_pct: number;
  precipitation_mm: number;
  rain_intensity_category: string;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  surface_pressure_hpa: number;
  weather_condition: string;
  provenance: {
    provider: string;
    authority: string;
    quality: string;
    retrieval_timestamp: string;
  };
}

export interface RiskMatrixResponse {
  district: string;
  hazard_type: string;
  hazard_index: number;
  exposure_index: number;
  vulnerability_index: number;
  composite_risk_score: number;
  risk_level: string;
  action_priority: string;
  provenance: Record<string, any>;
}

export interface DataSourceSummary {
  source_id: string;
  source_name: string;
  authority: string;
  source_type: string;
  authority_level: string;
  is_active: boolean;
  health_status: string;
  consecutive_failures: number;
  coverage: string;
  update_frequency: string;
  data_class: string;
  jurisdiction: string;
  supported_hazards: string[];
  authentication_required: boolean;
  last_success_iso?: string | null;
  last_failure_iso?: string | null;
}

export interface DataSourceHealthResponse {
  status: string;
  total_sources: number;
  online_count: number;
  degraded_count: number;
  failed_count: number;
  sources: Record<string, any>;
  generated_at_iso: string;
}

export interface ShowcaseStatus {
  step_index: number;
  step_name?: string | null;
  total_steps?: number;
  status: string;
  is_active: boolean;
  verdict?: string | null;
  severity?: string | null;
  revision_number?: number | null;
}
