# WeatherGPT — Tool Registry & Invocation Specification

**Document:** `05_TOOL_REGISTRY.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md)

---

## 1. Tool Gateway Architecture & Access Matrix

All tools in WeatherGPT are deterministic Python functions registered within the `ToolRegistry` and invoked via the `ToolGateway`. The LLM interacts with tools strictly through structured JSON function calls.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                             TOOL GATEWAY PIPELINE                          │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. Brain Permissions Check   → Validates Brain has access to requested tool│
│ 2. Parameter Sanitization    → Pydantic validation (ranges, coordinate bbox│
│ 3. Redis In-Memory Cache     → Returns cached result if TTL is active      │
│ 4. Deterministic Execution   → Queries API/PostGIS or runs SciPy/ET0 calc  │
│ 5. Provenance Metadata Stamp → Attaches timestamps, provider, & data source│
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Comprehensive Brain-to-Tool Permission Matrix

| Tool Identifier | General Brain | Farmer Brain | Researcher Brain | Analyst Brain | Ingest / Source | Cache TTL |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| `resolve_location` | ✅ | ✅ | ✅ | ✅ | Local Gazetteer / DB | 30 days |
| `get_current_weather` | ✅ | ✅ | ✅ | ✅ | IMD / Secondary API | 15 mins |
| `get_forecast` | ✅ | ✅ | ✅ | ✅ | IMD / GFS Blend | 1 hour |
| `get_rainfall` | ✅ | ✅ | ✅ | ✅ | Rain Gauges / Radar / NWP | 30 mins |
| `get_weather_alerts` | ✅ | ✅ | ✅ | ✅ | IMD CAP / District RSS | 10 mins |
| `get_nwp_data` | ❌ | ⚠️ Optional | ✅ | ✅ | GFS / ECMWF Grids | 6 hours |
| `compare_models` | ❌ | ❌ | ✅ | ✅ | Multi-NWP Comparator | 6 hours |
| `get_historical_weather` | ⚠️ Optional | ⚠️ Optional | ✅ | ✅ | IMD Gridded / ERA5 | Permanent |
| `get_dataset_metadata` | ❌ | ❌ | ✅ | ✅ | Metadata Catalog DB | 24 hours |
| `run_statistics` | ❌ | ❌ | ✅ | ✅ | SciPy / StatsEngine | Permanent |
| `run_correlation` | ❌ | ❌ | ✅ | ✅ | StatsEngine | Permanent |
| `compare_periods` | ❌ | ❌ | ✅ | ✅ | StatsEngine | Permanent |
| `compare_locations` | ❌ | ❌ | ✅ | ✅ | StatsEngine | Permanent |
| `export_dataset` | ❌ | ❌ | ✅ | ✅ | Data Exporter (CSV/GeoJSON)| 1 hour |
| `get_crop_profile` | ❌ | ✅ | ⚠️ Optional | ❌ | ICAR / Agrometeorology DB| 30 days |
| `get_crop_stage_context`| ❌ | ✅ | ⚠️ Optional | ❌ | Crop Stage Rule DB | 30 days |
| `get_soil_context` | ❌ | ✅ | ⚠️ Optional | ❌ | Soil Layer DB | 30 days |
| `calculate_irrigation_advisory`| ❌ | ✅ | ❌ | ❌ | FAO-56 $ET_0$ Engine | 1 hour |
| `check_spray_window` | ❌ | ✅ | ❌ | ❌ | Spray Rule Engine | 1 hour |
| `get_crop_weather_risk` | ❌ | ✅ | ❌ | ⚠️ Optional | Agro-hazard Engine | 1 hour |
| `run_gis_analysis` | ❌ | ❌ | ✅ | ✅ | PostGIS Engine | 1 hour |
| `get_exposure` | ❌ | ❌ | ❌ | ✅ | PostGIS Exposure DB | 24 hours |
| `intersect_hazard` | ❌ | ❌ | ❌ | ✅ | PostGIS Polygon Join | 30 mins |
| `run_risk_analysis` | ❌ | ❌ | ❌ | ✅ | Deterministic Risk Engine | 30 mins |
| `generate_map` | ⚠️ Optional | ⚠️ Optional | ✅ | ✅ | Map Specification Engine | Dynamic |
| `generate_dashboard` | ❌ | ❌ | ❌ | ✅ | Dashboard Spec Builder | Dynamic |

---

## 2. Weather Tools Category

### 2.1 `resolve_location`
* **Purpose:** Geocodes place names, districts, tehsils, or PIN codes into exact $(\text{lat}, \text{lon})$ coordinates and Administrative P-codes.
* **Input Parameters:**
  * `query_name` (`string`, required): Name of city, village, district, or 6-digit Indian PIN code.
  * `bias_state` (`string`, optional): State filter to resolve ambiguous district names.
* **Return Structure:**
  ```json
  {
    "name": "Ahmedabad",
    "district": "Ahmedabad",
    "state": "Gujarat",
    "country": "India",
    "latitude": 23.0225,
    "longitude": 72.5714,
    "elevation_m": 53.0,
    "admin_pcode": "IN-GJ-07"
  }
  ```
* **Failure Behavior:** If unresolved, returns empty list with suggested partial matches.

### 2.2 `get_current_weather`
* **Purpose:** Retrieves real-time surface meteorological observations for a coordinate.
* **Input Parameters:**
  * `latitude` (`float`, required): $-90.0$ to $90.0$ (Indian bbox: $6.0$ to $38.0$).
  * `longitude` (`float`, required): $-180.0$ to $180.0$ (Indian bbox: $68.0$ to $98.0$).
* **Return Structure:**
  ```json
  {
    "temperature_c": 31.4,
    "feels_like_c": 36.2,
    "relative_humidity_pct": 78,
    "wind_speed_kmh": 14.2,
    "wind_direction_deg": 240,
    "pressure_hpa": 1004.2,
    "precipitation_last_1h_mm": 2.4,
    "weather_condition": "light_rain_showers",
    "observation_time": "2026-08-29T11:00:00+05:30",
    "station_id": "IMD_42647"
  }
  ```

### 2.3 `get_forecast`
* **Purpose:** Provides hourly and daily weather forecasts up to 7 days ahead (core focus: next 24–72 hours).
* **Input Parameters:**
  * `latitude` (`float`, required), `longitude` (`float`, required).
  * `horizon_hours` (`int`, optional, default `72`, max `168`).
  * `temporal_resolution` (`string`, optional, enum: `["hourly", "daily"]`, default `"hourly"`).
* **Return Structure:** Contains structured arrays of temperature, dew point, rainfall sum, rain probability, wind speed/gust, and cloud cover.

### 2.4 `get_weather_alerts`
* **Purpose:** Retrieves official, authoritative IMD meteorological warnings and CAP (Common Alerting Protocol) feeds.
* **Input Parameters:**
  * `district_name` (`string`, optional) or `latitude`/`longitude`.
* **Return Structure:**
  ```json
  {
    "has_active_warning": true,
    "highest_warning_level": "Orange",
    "alerts": [
      {
        "source": "IMD",
        "hazard_type": "Heavy to Very Heavy Rain",
        "warning_color": "Orange",
        "severity": "Severe",
        "headline": "Orange Alert for Heavy to Very Heavy Rain in Pune District",
        "description": "Very heavy rainfall likely to occur at isolated places in the ghat areas.",
        "valid_from": "2026-08-29T08:30:00+05:30",
        "valid_until": "2026-08-30T08:30:00+05:30",
        "issuing_office": "RMC Mumbai / IMD Pune"
      }
    ]
  }
  ```

---

## 3. NWP & Multi-Model Tools Category

### 3.1 `get_nwp_data`
* **Purpose:** Fetches raw or interpolated Numerical Weather Prediction grid parameters (GFS 0.25°, ECMWF IFS open data).
* **Input Parameters:**
  * `model_name` (`string`, required, enum: `["gfs_0p25", "ecmwf_open"]`).
  * `latitude` (`float`, required), `longitude` (`float`, required).
  * `variables` (`array[string]`, required: `["apcp_surface", "tmp_2m", "ugrd_10m", "vgrd_10m", "rh_2m"]`).
  * `run_cycle` (`string`, optional, e.g. `"latest"`, `"00z"`, `"06z"`).

### 3.2 `compare_models`
* **Purpose:** Compares multi-model forecasts over the same geographic point and temporal window to evaluate model divergence.
* **Input Parameters:**
  * `latitude` (`float`, required), `longitude` (`float`, required).
  * `models` (`array[string]`, default: `["gfs_0p25", "ecmwf_open"]`).
  * `target_window_start` (`string`, ISO 8601), `target_window_end` (`string`, ISO 8601).
* **Return Structure:**
  ```json
  {
    "comparison_variable": "accumulated_rainfall_mm",
    "target_window": "2026-08-30",
    "model_values": {
      "gfs_0p25": 42.5,
      "ecmwf_open": 28.0
    },
    "spread_mm": 14.5,
    "agreement_level": "medium",
    "summary": "Models agree on rainfall occurrence but diverge on intensity (GFS indicates heavy downpour > 40mm; ECMWF predicts moderate 28mm)."
  }
  ```

---

## 4. Farmer Intelligence Tools Category

### 4.1 `calculate_irrigation_advisory`
* **Purpose:** Executes deterministic soil-water balance and FAO-56 Penman-Monteith crop evapotranspiration calculations.
* **Input Parameters:**
  * `location` (`object`, required: `{"latitude": float, "longitude": float}`).
  * `crop_name` (`string`, required: e.g., `"Wheat"`, `"Cotton"`, `"Paddy"`, `"Groundnut"`).
  * `crop_stage` (`string`, required: e.g., `"vegetative"`, `"flowering"`, `"grain_filling"`).
  * `soil_type` (`string`, optional, default `"medium_black_clay"`).
  * `last_irrigation_date` (`string`, optional).
* **Return Structure:**
  ```json
  {
    "irrigation_action": "POSTPONE",
    "urgency": "high",
    "reference_et0_mm": 4.1,
    "crop_kc": 1.15,
    "crop_water_demand_mm": 4.71,
    "forecast_rainfall_48h_mm": 38.0,
    "net_water_balance_deficit_mm": -33.29,
    "rationale": "Upcoming 48h rainfall (38.0mm) substantially exceeds crop demand (4.71mm/day). Irrigation will lead to soil saturation and root rot.",
    "actionable_steps": [
      "Withhold irrigation for the next 72 hours.",
      "Inspect field drainage to prevent standing water."
    ]
  }
  ```

### 4.2 `check_spray_window`
* **Purpose:** Evaluates chemical spray feasibility based on wind gust, rain probability, and post-spray rain-free intervals.
* **Input Parameters:**
  * `latitude` (`float`, required), `longitude` (`float`, required).
  * `target_date` (`string`, required, ISO 8601).
* **Return Structure:**
  ```json
  {
    "is_suitable": false,
    "optimal_time_window": null,
    "limiting_factors": [
      "High wind speed (24 km/h exceeds 15 km/h limit)",
      "Rain probability (75% exceeds 30% limit)"
    ],
    "recommendation": "Unsuitable for pesticide or foliar spray due to high risk of spray drift and chemical wash-off."
  }
  ```

---

## 5. Historical & Research Tools Category

### 5.1 `get_historical_weather`
* **Purpose:** Fetches daily or monthly continuous climate time-series from authoritative historical archives (IMD 0.25° gridded or ERA5).
* **Input Parameters:**
  * `latitude` (`float`, required), `longitude` (`float`, required).
  * `start_date` (`string`, required, YYYY-MM-DD), `end_date` (`string`, required, YYYY-MM-DD).
  * `variables` (`array[string]`, required: `["rainfall", "tmax", "tmin"]`).
* **Validation:** Date range must not exceed 50 years per single query.

### 5.2 `run_statistics`
* **Purpose:** Computes rigorous statistical summaries, Mann-Kendall monotonic trend tests, Sen's slope, and extreme percentiles.
* **Input Parameters:**
  * `data_series` (`array[float]`, required).
  * `timestamps` (`array[string]`, required).
  * `statistical_tests` (`array[string]`, required: `["mean", "std", "mann_kendall", "sens_slope", "percentiles"]`).
* **Return Structure:**
  ```json
  {
    "sample_size": 30,
    "mean": 842.5,
    "std_dev": 124.8,
    "percentiles": {"p10": 680.2, "p50": 835.0, "p90": 1012.4},
    "mann_kendall": {
      "tau": -0.32,
      "p_value": 0.018,
      "trend_direction": "decreasing",
      "statistically_significant": true,
      "significance_alpha": 0.05
    },
    "sens_slope": {
      "slope": -4.82,
      "units": "mm/year"
    }
  }
  ```

---

## 6. GIS & Spatial Risk Tools Category

### 6.1 `intersect_hazard`
* **Purpose:** Performs PostGIS vector intersections between an active hazard polygon (e.g., IMD warning zone or NWP heavy rain contour) and district/infrastructure spatial layers.
* **Input Parameters:**
  * `hazard_geojson` (`object`, required) or `warning_id` (`string`).
  * `exposure_layer` (`string`, enum: `["districts", "roads_highways", "population", "crop_zones"]`).
* **Return Structure:**
  ```json
  {
    "intersected_districts": [
      {"name": "Surat", "exposed_area_pct": 84.5, "estimated_population": 4800000},
      {"name": "Navsari", "exposed_area_pct": 62.1, "estimated_population": 850000}
    ],
    "infrastructure_impact": {
      "highways_km_exposed": 142.6,
      "major_substations_count": 8
    }
  }
  ```

### 6.2 `run_risk_analysis`
* **Purpose:** Computes deterministic risk scores combining hazard percentile, exposure percentage, and regional vulnerability.
* **Input Parameters:**
  * `hazard_percentile` (`float`, $0.0$ to $100.0$).
  * `exposure_index` (`float`, $0.0$ to $1.0$).
  * `vulnerability_score` (`float`, $0.0$ to $1.0$).
* **Calculation:** $\text{Score} = \text{Hazard Weight} \times 0.5 + \text{Exposure} \times 0.3 + \text{Vulnerability} \times 0.2$.
