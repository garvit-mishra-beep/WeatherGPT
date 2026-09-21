# WeatherGPT — Detailed Product Requirements Document (PRD)

**Document Type:** Product Requirements Document
**Product:** WeatherGPT
**Version:** MVP v1.0
**Platform:** Mobile-first conversational AI platform
**Primary Geography:** India
**Primary Data Authority:** India Meteorological Department (IMD)
**Core Technology:** LLM + Weather Data + NWP + GIS + Deterministic Analytics
**Voice:** Optional / lowest priority
**Development Model:** Modular, tool-based architecture

---

# 1. Project Description

**WeatherGPT** is an AI-powered, multilingual weather intelligence platform that converts complex meteorological information into **understandable, contextual and actionable information**.

The platform is designed around a simple observation:

> People do not only need weather data. They need to understand what the weather data means for their specific situation.

A general user may ask:

> "Will it rain tomorrow?"

A farmer may ask:

> "Should I irrigate my wheat tomorrow?"

A researcher may ask:

> "How has rainfall changed in this district over the last 20 years?"

An analyst may ask:

> "Which areas are most exposed to the expected heavy rainfall?"

All four questions concern weather, but the **required reasoning, data and output are different**.

WeatherGPT therefore introduces multiple intelligence workflows, called **Brains**, operating over a shared evidence and analytics layer.

```text
                         WEATHERGPT
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Weather            NWP              GIS
             │                │                │
             └────────────────┼────────────────┘
                              │
                       Analytics Layer
                              │
                         LLM / AI Layer
                              │
                  ┌───────────┼───────────┐
                  │           │           │
               General      Farmer    Researcher
                                          │
                                       Analyst
```

The core innovation is therefore **not simply AI + weather API**.

It is the conversion of:

> **Meteorological evidence → analysis → context → decision intelligence**

The existing technical research similarly identifies the strongest proposition as a grounded system combining authoritative data, NWP, GIS, transparent analytics, agricultural rules and a tool-using LLM. 

---

# 2. Problem Statement

Weather information is distributed across multiple systems:

* Government meteorological portals
* Forecast APIs
* Weather observations
* NWP models
* Historical datasets
* Satellite products
* Radar products
* Agricultural advisories
* Disaster warnings
* GIS datasets

A user may therefore need to visit several different systems to answer one practical question.

For example:

```text id="k8h7sq"
Farmer
  ↓
Weather website
  ↓
Forecast
  ↓
Agricultural website
  ↓
Crop information
  ↓
Personal judgement
  ↓
Decision
```

WeatherGPT attempts to simplify this:

```text id="b9b8ab"
Farmer
  ↓
Question
  ↓
WeatherGPT
  ├── Weather
  ├── NWP
  ├── Crop context
  └── Agricultural rules
  ↓
Recommendation
```

The platform therefore addresses the **weather information fragmentation and data-to-decision problem**.

---

# 3. Problem Statement from the Project Specification

The project specification identifies a need for an intelligent conversational system capable of providing:

1. Real-time weather information
2. Natural-language weather queries
3. NWP integration such as GFS/WRF
4. Extreme-weather alerts
5. Location-based forecasting
6. Multilingual support
7. Climate/historical analysis
8. Voice accessibility

It also identifies the need for:

* Mobile interface
* Backend meteorological integration
* AI/LLM query understanding
* Real-time data ingestion
* GIS
* Weather APIs
* Database infrastructure

WeatherGPT's architecture is designed around these requirements.

---

# 4. Product Vision

> **To make complex meteorological information understandable and useful to every user, while preserving the authority and traceability of the underlying weather data.**

The product should transform weather interaction from:

```text
"Find the weather"
```

into:

```text
"Understand what the weather means for me."
```

---

# 5. Product Mission

WeatherGPT will provide a single conversational interface through which users can:

* Retrieve weather information
* Understand forecasts
* Access warnings
* Ask agricultural questions
* Analyze historical weather
* Compare weather periods
* Explore NWP information
* Analyze geographic risk
* Generate maps and graphs
* Receive multilingual responses
* Export analytical results

---

# 6. Core Product Philosophy

The entire system is built around several principles.

## 6.1 Authoritative data first

Where official meteorological information is available, it should be treated as the authoritative source.

For India, **IMD is the primary authority**, especially for official warnings.

The research recommends IMD as the primary Indian source for warnings, nowcasts, forecasts, CAP alerts and agrometeorological guidance, subject to actual access and usage terms. 

---

## 6.2 AI interprets; AI does not invent weather

The LLM should never decide:

> "I think tomorrow's rainfall will be 43 mm."

Instead:

```text
Weather Source
     ↓
43 mm
     ↓
LLM
     ↓
"Rainfall is expected to be around 43 mm."
```

The numerical value must originate from the data layer.

---

## 6.3 Deterministic systems perform deterministic work

If the system needs to calculate:

* Mean
* Trend
* Anomaly
* Correlation
* Risk threshold
* Spatial intersection
* ET₀
* Statistical significance

those calculations should happen in dedicated engines.

The LLM explains the result.

---

## 6.4 Same evidence, different intelligence

A 50 mm rainfall forecast means different things to:

* General user → "Heavy rain is expected."
* Farmer → "You may need to reconsider irrigation."
* Researcher → "How does this compare to historical rainfall?"
* Analyst → "Which areas are exposed?"

Therefore, the same evidence layer feeds different Brain workflows.

---

# 7. Product Architecture

The complete conceptual architecture is:

```text id="y9xw9c"
                         📱 USER
                            │
                            ▼
                    MOBILE INTERFACE
                            │
                            ▼
                    INPUT NORMALIZER
                            │
             ┌──────────────┼──────────────┐
             │              │              │
          Language       Location       Date/Time
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                       AUTO ROUTER
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
    GENERAL              FARMER              RESEARCHER
                                                   │
                                                   ▼
                                                ANALYST
                            │
                            ▼
                    LLM ORCHESTRATOR
                            │
                            ▼
                      TOOL GATEWAY
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
     WEATHER               NWP                  GIS
        │                   │                   │
       IMD              GFS / NWP            PostGIS
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                    ANALYTICS ENGINE
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
          Statistics     Crop Rules      Risk Logic
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                      EVIDENCE PACKAGE
                            │
                            ▼
                           LLM
                            │
                    STRUCTURED OUTPUT
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
          TEXT          VISUALIZATION      DATA
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                           USER
```

The recommended architecture is intentionally modular, with ingestion adapters, normalized data, analytics/rules, PostGIS, RAG, an LLM router and UI separated rather than putting everything into one uncontrolled AI agent. 

---

# 8. User Types

WeatherGPT will have four primary intelligence modes.

| Brain          | Primary question                                                  |
| -------------- | ----------------------------------------------------------------- |
| **General**    | "What is happening with the weather?"                             |
| **Farmer**     | "What should I do because of the weather?"                        |
| **Researcher** | "What does the weather data show?"                                |
| **Analyst**    | "What is the weather-related risk and what should we prioritize?" |

---

# 9. General Brain

## 9.1 Purpose

The General Brain provides straightforward weather information without requiring specialized knowledge.

It is the default experience for everyday users.

---

## 9.2 Typical questions

Examples:

> What's the weather today?

> Will it rain tomorrow?

> What's the temperature?

> How strong will the wind be?

> Is there a warning in my district?

> What will the weather be this weekend?

---

## 9.3 Processing

```text id="s8l8r8"
User question
      ↓
Location
      ↓
Date/time
      ↓
Weather tool
      ↓
Data validation
      ↓
LLM explanation
      ↓
User
```

---

## 9.4 General outputs

The Brain may return:

* Current temperature
* Feels-like temperature
* Humidity
* Wind
* Rainfall
* Rain probability
* Forecast
* Weather condition
* Warning
* Source
* Data timestamp
* Basic graph
* Weather card

---

# 10. Farmer Brain

## 10.1 Purpose

The Farmer Brain transforms weather information into **agricultural decision support**.

It should answer:

> **"What does this weather mean for my crop, and what should I consider doing?"**

---

## 10.2 Farmer workflow

```text id="e5oqm2"
Weather Forecast
       +
Crop Information
       +
Crop Stage
       +
Soil/Farm Context
       ↓
Agricultural Rules
       ↓
Risk Evaluation
       ↓
Recommendation
       ↓
Farmer
```

---

# 11. Farmer Questions

The system should support questions such as:

### Rainfall

> What is the expected rainfall in my location over the next 24–48 hours?

> What is the probability and expected intensity of rainfall?

### Irrigation

> Should irrigation be scheduled or postponed?

### Spraying

> What is the suitable time for pesticide or fertilizer application?

### Extreme weather

> Are there upcoming extreme weather conditions that could affect my crop?

### Heat/frost

> What precautions should I take against heatwaves or frost?

### Harvesting

> Is the upcoming weather suitable for harvesting?

### Language

> Give me this advisory in my local language.

---

# 12. Farmer Personalization

Personalization is **optional**.

The system should not force the farmer to complete a large form.

Potential information includes:

### Crop

* Crop name
* Variety

### Crop lifecycle

* Sowing date
* Crop stage
* Expected harvest period

### Farm

* Farm location
* Farm size
* Irrigated/rain-fed status

### Soil

* Soil type
* Soil moisture
* Soil moisture measurement/source

### Irrigation

* Irrigation method
* Last irrigation
* Planned irrigation time
* Typical irrigation interval

The system asks only for information that materially improves the current answer.

---

# 13. Farmer Personalization Example

User:

> Should I irrigate tomorrow?

If location is known but crop is not:

```text id="7xv5o2"
System:
Which crop are you growing?
```

If crop is known but crop stage significantly affects the recommendation:

```text id="8e6kzv"
System:
What stage is the crop currently in?
```

If the available weather and crop information are sufficient:

```text id="m3xw1h"
System:
Answer directly.
```

This creates a **progressive personalization model**.

---

# 14. Farmer Irrigation Intelligence

For an advanced irrigation workflow, the deterministic engine can consider:

* Temperature
* Relative humidity
* Wind
* Solar radiation
* Crop coefficient
* Crop stage
* Forecast precipitation
* Soil moisture

The research describes an FAO-56 Penman–Monteith-based approach for ET₀ and combining crop water requirements with forecast rainfall and soil moisture. 

Conceptually:

```text id="t1tw1t"
Weather
   ↓
ET₀
   ↓
Crop coefficient
   ↓
Crop water requirement
   ↓
Expected rainfall
   +
Soil moisture
   ↓
Water balance
   ↓
Irrigation recommendation
```

This calculation should **not** be performed by the LLM.

---

# 15. Farmer Spraying Window

For spraying suitability, the system can evaluate:

* Rain probability
* Rain forecast
* Wind speed/gusts
* Relevant crop stage
* Applicable agronomic rules

The research uses rainfall probability and wind conditions as examples of rule-based screening. 

The output should be:

```text id="7u0a5c"
Suitable
OR
Not suitable
OR
Insufficient information
```

rather than pretending to provide guaranteed chemical effectiveness.

---

# 16. Farmer Safety

The Farmer Brain must refuse a definitive recommendation when required information is missing.

For example:

```text id="w2l7l3"
Unknown crop stage
+
Unknown soil condition
+
Critical decision
        ↓
Do not invent
        ↓
Ask for required information
```

The research recommends using grounded agricultural guidance when local information is insufficient rather than allowing the LLM to invent agronomic recommendations. 

---

# 17. Researcher Brain

## 17.1 Purpose

The Researcher Brain answers:

> **"What does the data tell us?"**

It is designed for historical, statistical and scientific analysis.

---

# 18. Researcher Questions

Examples:

> What are the historical weather trends for this region?

> Give me daily/hourly historical weather data.

> How has temperature changed?

> How has rainfall changed?

> What correlation exists between weather and crop yield?

> What climate-change trends can be identified?

> Can I download this dataset?

> Can I access the data through an API?

> What is the source and reliability of this dataset?

> Can you provide a data-quality score?

> Can I filter the data by location, date and variable?

---

# 19. Researcher Workflow

```text id="9ck8vi"
Research Question
       ↓
Intent extraction
       ↓
Location
       ↓
Time period
       ↓
Variables
       ↓
Dataset selection
       ↓
Data retrieval
       ↓
Validation
       ↓
Statistical engine
       ↓
Visualization
       ↓
LLM explanation
```

---

# 20. Research Dataset Metadata

Every dataset used by the Researcher Brain should have:

* Dataset name
* Provider
* Source
* Time coverage
* Spatial coverage
* Spatial resolution
* Temporal resolution
* Variables
* Units
* Missing-data information
* Processing methodology
* Update frequency

This is important because:

> A result without knowing what data produced it is not a reproducible research result.

---

# 21. Research Statistical Engine

Possible operations include:

### Descriptive

* Mean
* Median
* Minimum
* Maximum
* Standard deviation

### Weather

* Rainfall totals
* Temperature averages
* Extreme-event frequency
* Percentiles

### Climate

* Anomaly
* Trend
* Seasonal comparison
* Year comparison

### Statistical

* Correlation
* Mann–Kendall
* Sen's slope

The existing research specifically recommends Mann–Kendall and Sen's slope for trend analysis. 

---

# 22. Research Output

A research result should contain:

```text id="7thh4s"
Question
↓
Dataset
↓
Period
↓
Method
↓
Result
↓
Visualization
↓
Limitations
↓
Source
```

For example:

> Rainfall shows a decreasing trend over the selected period.

Then provide:

* Dataset
* Period
* Trend value
* Statistical significance
* Method
* Chart
* Missing-data information
* Source

---

# 23. Analyst Brain

## Purpose

The Analyst Brain addresses:

> **"What is the weather-related risk, where is it occurring, and what should be prioritized?"**

This Brain is particularly relevant to:

* Disaster managers
* Government agencies
* Business analysts
* Supply-chain planners
* Urban planners
* Infrastructure operators

---

# 24. Analyst Workflow

```text id="1slhkv"
Weather
+
Official Warning
+
NWP
+
Historical Baseline
+
GIS
+
Exposure
       ↓
Hazard Analysis
       ↓
Spatial Analysis
       ↓
Risk Context
       ↓
Priority
       ↓
Decision Support
```

---

# 25. Hazard vs Exposure vs Vulnerability

Risk should not be treated as a mysterious AI number.

The system should distinguish:

### Hazard

What weather event is occurring?

Example:

> Extreme rainfall.

### Exposure

What is located in the affected area?

Example:

> Population, roads, facilities.

### Vulnerability

How susceptible is the exposed system?

Example:

> Low-lying area or critical infrastructure.

Conceptually:

```text id="h7qk1u"
Hazard
+
Exposure
+
Vulnerability
↓
Risk Context
```

The research explicitly identifies this distinction as fundamental to operational weather intelligence. 

---

# 26. GIS Integration

GIS allows WeatherGPT to move from:

> "What is happening at this coordinate?"

to:

> "What areas and assets could be affected?"

The system can use PostGIS for spatial operations.

Example:

```text id="7k0tby"
IMD Warning Polygon
       ↓
ST_Intersects
       ↓
Districts
       +
Population
       +
Roads
       +
Critical facilities
       ↓
Affected-area analysis
```

This architecture is specifically recommended in the research. 

---

# 27. Analyst Risk Quantification

Risk scores should not be arbitrary.

The system may use deterministic thresholds based on historical distributions.

For example:

```text id="m1w8bw"
Forecast rainfall
      ↓
Historical percentile
      ↓
Hazard category
      +
Exposure
      ↓
Priority category
```

The research proposes historical extreme-event percentiles as one possible basis for deterministic hazard scoring. 

---

# 28. Multi-Model Intelligence

WeatherGPT should be able to compare model outputs.

Example:

```text id="5q1h4k"
GFS      → 80 mm
ECMWF    → 45 mm
IMD      → Heavy rainfall warning
```

The system should not simply average these values.

Instead:

```text id="x2k9d1"
Model agreement
       ↓
Low / Medium / High
       ↓
Explain disagreement
```

Until local verification exists, this should be described as **model agreement/disagreement**, not a scientifically calibrated probability of forecast correctness. 

---

# 29. Official Warning Handling

This is one of the most important safety requirements.

If IMD issues a warning:

```text id="2nqgq8"
IMD Warning
    ↓
WeatherGPT
    ├── Explain
    ├── Translate
    ├── Map
    └── Contextualize
```

But WeatherGPT must not:

```text id="b2z2cl"
Change warning level
Downgrade warning
Invent warning
Issue unofficial warning as official
```

The system can add interpretation without altering the original official warning.

---

# 30. Auto Router

Auto is responsible for understanding the user's objective.

It should identify:

* Intent
* Location
* Date/time
* Required context
* Brain
* Required tools

---

## 30.1 Routing logic

```text id="j74a8r"
User Question
      ↓
Language
      ↓
Intent
      ↓
Context
      ↓
Goal
      ↓
Brain
```

### Examples

**"Will it rain tomorrow?"**

→ General

**"Should I irrigate tomorrow?"**

→ Farmer

**"Compare rainfall over the last 20 years."**

→ Researcher

**"Which areas are at greatest risk?"**

→ Analyst

---

# 31. Auto Does Not Route by Keyword Alone

Consider:

> "How will tomorrow's rain affect my wheat?"

Keywords:

* Rain
* Wheat

But the actual goal is an agricultural decision.

Therefore:

```text id="i1r4o8"
Topic = weather
Context = crop
Goal = decision
        ↓
Farmer
```

The router should prioritize **intent and desired outcome**.

---

# 32. Brain Switching

The selected Brain does not have to remain fixed forever.

Example:

**User:**

> What's tomorrow's rainfall?

→ General

**User:**

> Compare it with last year.

→ Researcher

**User:**

> Now tell me if it is risky for my wheat.

→ Farmer

Conversation context allows the system to switch intelligently.

---

# 33. Ambiguous Queries

If the system cannot safely determine the Brain:

> "What is the weather risk?"

It can ask:

> "Are you asking about farming, business operations, disaster risk, or general weather?"

This prevents incorrect routing.

---

# 34. Input Contract

The standardized LLM input should contain:

```json id="f7kn5x"
{
  "query": "...",
  "language": "...",
  "location": {
    "name": "...",
    "latitude": null,
    "longitude": null
  },
  "datetime": "...",
  "conversation_history": [],
  "selected_brain": "auto",
  "requested_output": []
}
```

---

# 35. Location Rules

Location may come from:

1. User's explicit input
2. Device GPS, if permission is granted
3. Saved user preference/context
4. Clarification from the user

If no reliable location is available and the question requires it:

> **Ask the user.**

Never silently assume a location.

---

# 36. Date/Time Rules

The system should resolve natural-language time expressions.

Examples:

```text id="s5n11c"
Today
Tomorrow
Day after tomorrow
Next 24 hours
Next 48 hours
This week
Next week
Specific date
```

The date should be resolved by the application/backend rather than asking the LLM to guess the current date.

---

# 37. Tool Calling

The LLM communicates with external systems through a controlled Tool Gateway.

```text id="t9x9q0"
LLM
 ↓
Tool Request
 ↓
Tool Gateway
 ↓
Validation
 ↓
Service
 ↓
Verified Result
 ↓
LLM
```

This keeps the LLM separate from raw databases and APIs.

---

# 38. Weather Tools

Core tools include:

```text id="0xx4gf"
get_current_weather()
get_forecast()
get_rainfall()
get_weather_alerts()
resolve_location()
```

---

# 39. NWP Tools

The logical tool layer may contain:

```text id="o0e4v9"
get_nwp_data()
get_gfs_forecast()
get_ecmwf_forecast()
get_wrf_output()
compare_models()
```

However, a tool should only be enabled when the underlying data source is actually available.

---

# 40. Research Tools

```text id="q7rrph"
get_historical_weather()
get_dataset_metadata()
run_statistics()
run_correlation()
compare_periods()
compare_locations()
generate_dataset()
export_dataset()
```

---

# 41. GIS Tools

```text id="7p5g1u"
resolve_location()
run_gis_analysis()
get_exposure()
intersect_hazard()
generate_map()
```

---

# 42. Farmer Tools

```text id="rxq2t5"
get_crop_profile()
get_crop_stage_context()
get_soil_context()
get_irrigation_context()
calculate_irrigation_advisory()
check_spray_window()
get_crop_weather_risk()
```

---

# 43. Analyst Tools

```text id="u0v4yn"
run_anomaly_analysis()
run_risk_analysis()
run_forecast_verification()
run_gis_analysis()
generate_map()
generate_graph()
generate_dashboard()
generate_report()
```

---

# 44. Tool Permission System

Each Brain should have controlled tool access.

| Tool            |  General |   Farmer | Researcher | Analyst |
| --------------- | -------: | -------: | ---------: | ------: |
| Current weather |        ✅ |        ✅ |          ✅ |       ✅ |
| Forecast        |        ✅ |        ✅ |          ✅ |       ✅ |
| Warnings        |        ✅ |        ✅ |          ✅ |       ✅ |
| Crop tools      |        ❌ |        ✅ |   Optional |       ❌ |
| Historical data | Optional | Optional |          ✅ |       ✅ |
| NWP             |  Limited | Optional |          ✅ |       ✅ |
| Statistics      |        ❌ |  Limited |          ✅ |       ✅ |
| GIS             |  Limited |  Limited |          ✅ |       ✅ |
| Risk analysis   |        ❌ |  Limited |   Optional |       ✅ |
| Dataset export  |        ❌ |        ❌ |          ✅ |       ✅ |
| Dashboard       |        ❌ |  Limited |   Optional |       ✅ |

---

# 45. Standard Tool Request

Example:

```json id="8trnqs"
{
  "tool": "get_forecast",
  "request_id": "abc123",
  "arguments": {
    "location": {
      "latitude": 23.0225,
      "longitude": 72.5714
    },
    "start_time": "...",
    "end_time": "...",
    "resolution": "hourly"
  }
}
```

---

# 46. Standard Tool Response

```json id="l5v2hy"
{
  "request_id": "abc123",
  "status": "success",
  "tool": "get_forecast",
  "data": {},
  "source": [],
  "retrieved_at": "...",
  "quality": {
    "freshness": "...",
    "completeness": "...",
    "confidence": null
  },
  "error": null
}
```

The exact tool schemas will be maintained separately in the technical API specification.

---

# 47. Data Source Architecture

WeatherGPT should not hard-code a single provider into the entire application.

Instead:

```text id="e1u7d5"
             DATA SOURCES
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
      IMD        GFS       Other
       │          │          │
       └──────────┼──────────┘
                  ▼
          SOURCE ADAPTERS
                  ↓
          NORMALIZED DATA
                  ↓
       WeatherGPT Intelligence
```

This means changing an API provider does not require rebuilding the entire LLM system.

---

# 48. IMD Strategy

IMD is the primary Indian meteorological authority.

It should be used wherever accessible for:

* Official warnings
* Forecast products
* Nowcasts
* Rainfall information
* Agricultural advisories
* Relevant official observations/products

Current access is still a project dependency.

The research explicitly states that exact IMD endpoint access, authentication, rate limits and access rights must be verified before deployment. 

---

# 49. Secondary Weather Sources

Until IMD API access is available, the system should be developed against accessible secondary sources.

The architecture should support:

* GFS
* ECMWF where permitted
* Other approved weather APIs

These are **fallback/secondary sources**, not replacements for official IMD warnings.

---

# 50. NWP Strategy

NWP is a major part of the project.

The system should integrate NWP information rather than pretending that the LLM itself is a numerical weather model.

### Recommended architecture

```text id="p8h1c2"
GFS
 ↓
NWP data
 ↓
Normalization
 ↓
WeatherGPT
```

If an existing trusted WRF output becomes available:

```text id="t0h1z8"
WRF output
 ↓
NWP adapter
 ↓
WeatherGPT
```

### Important MVP boundary

**Do not build a new operational WRF forecasting system as part of the core MVP.**

The research explicitly recommends **not running WRF in the MVP**, because the infrastructure and validation burden is too large. 

---

# 51. Historical Data Architecture

Historical data should be stored/versioned independently from live weather.

```text id="m4z6x5"
Historical Dataset
      ↓
Metadata
      ↓
Database
      ↓
Research Tools
      ↓
Analytics
```

The system should preserve:

* Dataset version
* Retrieval date
* Period
* Variables
* Resolution
* Processing

---

# 52. Analytics Engine

The analytics engine is one of the most important components.

It should handle:

### Research

* Trend
* Anomaly
* Correlation
* Percentiles
* Historical ranking
* Statistical significance

### Farmer

* ET₀
* Water balance
* Crop-stage thresholds
* Weather windows

### Analyst

* Hazard thresholds
* Exposure
* Spatial intersections
* Model divergence

---

# 53. GIS Data Model

The spatial database can contain:

```text id="ujf9f3"
Locations
States
Districts
Sub-districts
Weather grids
NWP grids
Warning polygons
Population layers
Roads
Critical facilities
Elevation
Agricultural areas
```

Not all layers need to be implemented immediately.

The important architectural requirement is that they can be added without redesigning the LLM.

---

# 54. Visualization System

The LLM should not generate actual charts or maps.

Instead:

```text id="u6g8t2"
LLM
 ↓
Visualization specification
 ↓
Visualization engine
 ↓
Graph / Map
```

For example:

```json id="q1x6sd"
{
  "type": "map",
  "title": "Heavy Rainfall Risk",
  "data_source": "gis_analysis",
  "parameters": {}
}
```

The frontend then renders the actual map.

---

# 55. Output Contract

All Brains should return structured output.

```json id="4h5n5b"
{
  "brain": "farmer",
  "language": "hi",
  "answer": "...",
  "summary": "...",
  "data": {},
  "recommendation": null,
  "alert": null,
  "visualizations": [],
  "sources": [],
  "timestamps": [],
  "confidence": null,
  "limitations": []
}
```

Not every field has to contain a value for every query.

---

# 56. Output Types

WeatherGPT should be capable of producing:

### Text

Normal conversational answer.

### Weather card

Temperature, rainfall, humidity, wind, warning.

### Recommendation

Farmer action-support.

### Table

Research data.

### Graph

Historical/statistical analysis.

### Map

GIS/weather-risk analysis.

### Dashboard

Analyst workflow.

### Dataset

CSV/JSON.

### Report

PDF/Excel where supported.

---

# 57. Evidence and Sources

Each important answer should identify:

* Source
* Timestamp
* Dataset/model
* Processing method where relevant

For example:

```text id="7t3s8k"
Source:
IMD

Forecast:
GFS

Retrieved:
...

Analysis:
Historical percentile comparison
```

This makes the system auditable.

---

# 58. Confidence and Uncertainty

WeatherGPT should not generate arbitrary AI confidence numbers.

Instead, it should communicate evidence quality.

Factors may include:

* Source authority
* Data freshness
* Data completeness
* Forecast horizon
* Spatial match
* Model agreement
* Statistical uncertainty

For model comparison, the system should communicate **agreement/disagreement**, not pretend that model spread automatically equals calibrated probability. 

---

# 59. Data Freshness

Every live result should have a retrieval/update timestamp.

For example:

```text id="8j8z3m"
Forecast updated:
10:30 IST

Data valid for:
30 Aug 2026
```

This is especially important when cached information is being used.

---

# 60. Three-Day Forecast Cache

The system should maintain:

```text id="g7z0q3"
Today
Tomorrow
Day after tomorrow
```

When the date changes:

```text id="d8w1w9"
Old data
   ↓
Remove expired day
   ↓
Shift forecast
   ↓
Fetch new third day
```

The cache should never make yesterday's information appear to be today's forecast.

---

# 61. Low-Connectivity Behavior

The platform should support graceful degradation.

```text id="l0o7er"
Live Data
   ↓
Available?
 ├── YES → Fresh result
 │
 └── NO
       ↓
    Cached data?
       │
      YES
       ↓
Show data + timestamp
```

If neither live nor cached data is appropriate:

> The system should clearly say that current data could not be retrieved.

It should never invent a value.

---

# 62. Multilingual Architecture

Language is an interface layer across the entire system.

```text id="x2o9ju"
User Language
      ↓
Language Detection
      ↓
Intent
      ↓
Tools
      ↓
Evidence
      ↓
LLM
      ↓
Requested Language
```

The supported MVP languages are:

* English
* Hindi
* Bengali
* Marathi
* Gujarati

The underlying numerical evidence should remain identical regardless of language.

---

# 63. Code-Mixed Language

The system should support queries such as:

> "Kal mere wheat ko irrigation karna chahiye?"

The system should understand:

```text id="g6f6eu"
Language = Hindi/English mixed
Intent = Irrigation
Crop = Wheat
Time = Tomorrow
Brain = Farmer
```

Then produce a natural response in the user's preferred language.

---

# 64. Voice

Voice is intentionally separated from the core architecture.

If implemented:

```text id="6v0b6v"
Voice Input
 ↓
Speech Recognition
 ↓
Text
 ↓
Auto
 ↓
Brain
 ↓
Tools
 ↓
LLM
 ↓
TTS
 ↓
Voice Output
```

Voice should not change the underlying intelligence system.

It is therefore safe to add later.

---

# 65. RAG

RAG should be used for **knowledge and document grounding**, not for live weather numbers.

Suitable RAG material:

* IMD documentation
* Agricultural guidance
* Methodology
* Warning terminology
* Dataset documentation
* Domain knowledge

Live numerical weather information should come from live data tools/database systems.

The research similarly scopes RAG toward documentation/knowledge rather than using it as the live numerical weather source. 

---

# 66. Backend

The backend acts as the central coordinator.

```text id="g8b9z5"
                    FastAPI
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
     LLM             Tools           Database
       │               │                │
       │        ┌──────┼──────┐         │
       │        ▼      ▼      ▼         │
       │     Weather   NWP    GIS       │
       │                                  │
       └───────────────┬──────────────────┘
                       ▼
                   Response
```

The backend should be responsible for:

* Authentication
* Routing
* Tool execution
* Data validation
* Source tracking
* Caching
* Database access
* Error handling

---

# 67. Two-Laptop Architecture

For development, the system can be split across two laptops.

### LLM laptop

```text id="w8e2xk"
LLM Runtime
Auto Router
Brain Logic
```

### Backend/Data laptop

```text id="h8p1k4"
FastAPI
Weather APIs
NWP
GIS
PostGIS
Analytics
```

Communication:

```text id="5c9u6g"
📱 Phone
   ↓
Laptop 2
   ↓
Laptop 1
   ↓
Laptop 2
   ↓
📱 Phone
```

This separation allows the LLM machine to focus on inference while the second machine handles data and services.

---

# 68. Database Architecture

The database should logically contain:

```text id="b3r6y5"
Users
User Preferences
Conversations
Locations
Farmer Profiles
Weather Observations
Forecasts
NWP Runs
Warnings
Historical Dataset Metadata
GIS Layers
Analysis Results
Tool Calls
Sources
```

PostGIS extends PostgreSQL for spatial data.

---

# 69. Security Requirements

API credentials must remain on the backend.

The mobile application should never directly receive:

* Weather API keys
* Database credentials
* LLM provider secrets
* Internal service credentials

The backend should validate tool parameters before execution.

---

# 70. Failure Handling

Every external dependency can fail.

### Weather API fails

Use permitted fallback or cached data.

### IMD unavailable

Do not claim current official status.

### NWP unavailable

Do not fabricate model output.

### Database unavailable

Return controlled error.

### LLM unavailable

Return system-level failure.

### Location unavailable

Ask user.

### Historical data incomplete

Show limitation.

### Model disagreement

Display disagreement.

The research specifically recommends visibly marking unavailable official feeds and avoiding claims of current official status when the official source cannot be retrieved. 

---

# 71. Mobile UX

The mobile interface should prioritize **conversation first**.

The user should be able to:

1. Open WeatherGPT.
2. Ask a question.
3. Provide location if necessary.
4. Receive an answer.
5. Ask follow-up questions.

Advanced functionality appears when relevant.

For example:

```text id="u4xw83"
Research question
      ↓
Answer
      ↓
"View chart"
      ↓
Chart
```

Rather than displaying every possible feature at once.

---

# 72. Brain Selection in Mobile

The UI may provide:

```text
Auto
General
Farmer
Researcher
Analyst
```

### Auto

Recommended default.

### Manual Brain selection

Useful for users who know exactly what they need.

Manual selection should override Auto routing where appropriate.

---

# 73. Conversation Context

Conversation history should allow contextual follow-ups.

Example:

**User:**

> What's the weather tomorrow in Ahmedabad?

**System:**

> ...

**User:**

> Should I irrigate?

The system should understand that:

* Location = Ahmedabad
* Date = tomorrow

But it may still need:

* Crop

So it asks only for the missing critical information.

---

# 74. General Data Flow

```text id="v8m0ws"
User Query
 ↓
Input Normalization
 ↓
Auto Router
 ↓
Brain
 ↓
Tool Selection
 ↓
Tool Gateway
 ↓
Data Retrieval
 ↓
Analytics
 ↓
Evidence Package
 ↓
LLM
 ↓
Structured Response
 ↓
Mobile UI
```

---

# 75. Farmer Data Flow

```text id="u5n1p3"
User
 ↓
Farmer Brain
 ↓
Crop Context
 ↓
Weather
 ↓
Soil
 ↓
Agricultural Rules
 ↓
Risk / Water Balance
 ↓
Recommendation
 ↓
LLM Explanation
```

---

# 76. Researcher Data Flow

```text id="k3j8r1"
Research Question
 ↓
Dataset Selection
 ↓
Historical Data
 ↓
Validation
 ↓
Statistics
 ↓
Chart
 ↓
LLM Explanation
```

---

# 77. Analyst Data Flow

```text id="x7y2m1"
Analyst Question
 ↓
Weather + Warning
 ↓
NWP
 ↓
Historical Baseline
 ↓
GIS
 ↓
Exposure
 ↓
Risk Analysis
 ↓
Map / Dashboard
 ↓
Decision Support
```

---

# 78. Output Safety Model

The final LLM answer should be generated only from the available evidence.

Conceptually:

```text id="u1f6y4"
Tool Results
     ↓
Evidence Validator
     ↓
LLM
     ↓
Output Validator
     ↓
User
```

This reduces the risk of hallucinated values.

---

# 79. What Happens When Data Is Missing?

The system has three possible responses:

### Sufficient evidence

Answer normally.

### Partially sufficient

Answer with limitation.

### Insufficient

Ask for information or refuse a definitive answer.

Example:

```text id="p8o1p9"
No soil moisture
+
Irrigation decision
       ↓
Cannot confidently calculate
       ↓
Ask for soil moisture
```

---

# 80. Product-Level Guardrails

WeatherGPT should never:

* Fabricate weather values
* Fabricate sources
* Modify official warning levels
* Claim unsupported precision
* Claim village-level precision when data doesn't support it
* Produce arbitrary risk scores
* Give unsafe agricultural instructions
* Present experimental analysis as official
* Hide stale data
* Hide source disagreement

---

# 81. What Makes WeatherGPT Different

A conventional weather application:

```text id="v0n1k6"
Weather API
    ↓
Weather screen
```

WeatherGPT:

```text id="e4c7d2"
User
 ↓
Natural-language question
 ↓
Intent
 ↓
Brain
 ↓
Data selection
 ↓
NWP / Weather / GIS / History
 ↓
Deterministic analysis
 ↓
Context
 ↓
LLM
 ↓
Decision intelligence
```

This is the core innovation.

---

# 82. Innovation Areas

## 82.1 Multi-Brain Intelligence

Different user goals produce different reasoning workflows.

## 82.2 Evidence-Grounded LLM

The LLM is connected to actual tools rather than being treated as a weather oracle.

## 82.3 NWP Comparison

The system can compare model signals rather than blindly trusting one model.

## 82.4 GIS Impact Translation

The system can move from weather conditions to affected geographic areas.

## 82.5 Agricultural Decision Intelligence

Weather can be combined with crop context.

## 82.6 Reproducible Research

Historical analysis includes dataset, method and result.

## 82.7 Multilingual Intelligence

Language becomes an accessibility layer rather than a separate product.

---

# 83. MVP Scope

## Must Have

### AI

* LLM
* Auto Router
* General Brain
* Farmer Brain
* Researcher Brain
* Analyst Brain
* Tool calling
* Structured outputs

### Weather

* Current weather
* Forecast
* Rainfall
* Alerts
* Location

### NWP

* GFS or another accessible NWP stream
* NWP normalization
* NWP comparison where available

### GIS

* PostGIS
* Administrative boundaries
* Basic spatial analysis
* Weather/GIS mapping

### Research

* Historical data
* Basic statistical analysis
* Trend/anomaly
* Visualization

### Farmer

* Crop context
* Weather-aware advisory
* Irrigation/spray-window logic where sufficient data exists

### Mobile

* Chat
* Auto/manual Brain
* Location
* Weather cards
* Maps
* Graphs
* Multilingual text

---

# 84. Should Have

* Advanced farmer personalization
* Multiple model comparison
* More advanced risk analysis
* Dataset export
* Dashboard
* Reports
* More GIS layers
* More historical analysis
* Advanced confidence/evidence presentation

---

# 85. Optional / Last Priority

### Voice

* Whisper/ASR
* TTS
* Voice interaction

The architecture is intentionally designed so voice can be added without changing the Brain or data layer.

---

# 86. Explicitly Out of Core MVP

The research recommends excluding several high-complexity capabilities from the MVP:

* Self-trained LLM
* Self-trained NWP
* National-scale WRF
* Real-time WRF execution
* Complete satellite analytics
* National vulnerability modeling
* Exact village-level forecast claims
* Autonomous official warning issuance
* Disease diagnosis
* Prescription-like chemical recommendations
* Full 22-language voice
* Kafka/Kubernetes/WIS2 infrastructure without a concrete operational need



---

# 87. Testing Requirements

Testing should be task-based.

## General

Can the user understand the forecast?

## Farmer

Is the recommendation relevant and safely bounded?

## Researcher

Are calculations correct and reproducible?

## Analyst

Is the spatial and operational interpretation useful?

## System

Test:

* Routing
* Evidence coverage
* Hallucination
* Warning preservation
* Latency
* Data freshness
* Failure handling
* Multilingual output
* Model disagreement

These dimensions are consistent with the project's existing validation framework. 

---

# 88. Key Demonstration Scenarios

## Demo 1 — General

> "What will the weather be tomorrow in Ahmedabad?"

Expected:

```text
Location
+
Forecast
+
Rain
+
Temperature
+
Warning
```

---

## Demo 2 — Farmer

> "Should I irrigate my wheat tomorrow?"

Expected:

```text
Forecast
+
Crop
+
Crop stage
+
Agricultural logic
↓
Recommendation
```

---

## Demo 3 — Researcher

> "Compare the last ten monsoons in this district."

Expected:

```text
Historical dataset
↓
Monsoon totals
↓
Anomaly
↓
Ranking
↓
Chart
↓
Explanation
```

---

## Demo 4 — Analyst

> "Which areas are most exposed to heavy rainfall?"

Expected:

```text
IMD warning
+
NWP
+
GIS
+
Exposure
↓
Priority areas
↓
Map
```

These demonstration workflows are specifically aligned with the technical research recommendations. 

---

# 89. Data-to-Decision Pipeline

This is the central product pipeline:

```text id="r5y0a1"
                 DATA
                  ↓
          Weather / IMD / NWP
                  ↓
              NORMALIZE
                  ↓
              VALIDATE
                  ↓
              ANALYZE
                  ↓
         ┌────────┼────────┐
         ▼        ▼        ▼
       Crop     History    GIS
         │        │        │
         └────────┼────────┘
                  ▼
               EVIDENCE
                  ↓
                LLM
                  ↓
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      Explain   Recommend  Visualize
        │         │         │
        └─────────┼─────────┘
                  ▼
                USER
```

---

# 90. Complete Product Architecture

```text id="v3j8w2"
                         ┌───────────────────┐
                         │       USER        │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   MOBILE APP      │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ INPUT NORMALIZER  │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   AUTO ROUTER     │
                         └─────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
        ┌──────────┐         ┌──────────┐        ┌────────────┐
        │ GENERAL  │         │  FARMER  │        │ RESEARCHER │
        └────┬─────┘         └────┬─────┘        └─────┬──────┘
             │                    │                     │
             │                    │                ┌────▼─────┐
             │                    │                │ ANALYST  │
             │                    │                └────┬─────┘
             └────────────────────┼─────────────────────┘
                                  │
                                  ▼
                         ┌───────────────────┐
                         │ LLM ORCHESTRATOR  │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   TOOL GATEWAY    │
                         └─────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
       ┌────────────┐       ┌────────────┐       ┌────────────┐
       │  WEATHER   │       │    NWP     │       │    GIS     │
       └─────┬──────┘       └─────┬──────┘       └─────┬──────┘
             │                    │                    │
            IMD              GFS / NWP             PostGIS
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                         ┌───────────────────┐
                         │ ANALYTICS ENGINE  │
                         └─────────┬─────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
                Statistics      Crop Rules     Risk Logic
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ EVIDENCE PACKAGE  │
                         └─────────┬─────────┘
                                   │
                                   ▼
                              ┌──────────┐
                              │   LLM    │
                              └────┬─────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ STRUCTURED OUTPUT │
                         └─────────┬─────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
             TEXT             VISUALS              DATA
                │                  │                  │
                ▼                  ▼                  ▼
             Answer          Map / Graph        CSV / JSON
                │
                └──────────────────┬──────────────────┘
                                   ▼
                                  USER
```

---

# 91. Final Product Definition

WeatherGPT should ultimately be understood as:

> **A grounded, multilingual weather decision-intelligence platform that combines authoritative Indian meteorological information, accessible NWP data, historical datasets, deterministic analytics, agricultural knowledge and GIS to provide role-specific conversational intelligence.**

The four Brains provide different interpretations of the same evidence:

### General Brain

**Understand the weather.**

### Farmer Brain

**Act under weather uncertainty.**

### Researcher Brain

**Understand what the historical data shows.**

### Analyst Brain

**Understand risk, impact and priority.**

The LLM sits above these systems as the **language, reasoning-orchestration and explanation layer**, while the underlying data, NWP, GIS and deterministic analytics remain the sources of truth. This separation is the key architectural decision that makes WeatherGPT technically defensible rather than simply an AI chatbot connected to a weather API. 

---

# 92. One-Line Architecture

> **WeatherGPT = User Intent + Authoritative Weather Evidence + NWP + GIS + Deterministic Analytics + Domain Brains + LLM Explanation.**

And the single most important rule for the entire project is:

> **The AI should never invent the weather; it should understand the question, retrieve the right evidence, perform or invoke the right analysis, and explain the result to the user.** 
