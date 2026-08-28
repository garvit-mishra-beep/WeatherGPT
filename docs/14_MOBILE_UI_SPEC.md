# WeatherGPT — Mobile UI & Conversational UX Specification

**Document:** `14_MOBILE_UI_SPEC.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [13_MULTILINGUAL_SPEC.md](13_MULTILINGUAL_SPEC.md)

---

## 1. UX Philosophy: Conversational-First with Progressive Disclosure

WeatherGPT is designed as a **conversational-first mobile application**. Users interact through natural dialogue, while rich structured UI cards, charts, and interactive maps appear contextually based on the active Domain Brain's response.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                         CORE UX DESIGN PRINCIPLES                          │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. Conversational Simplicity: Launch directly into an intuitive chat stream │
│    without mandatory multi-step onboarding forms.                          │
│ 2. Progressive UI Disclosure: Render weather cards, agronomic advisories,  │
│    or spatial maps only when relevant to the user's immediate question.    │
│ 3. Glancable High-Priority Warnings: Official IMD Red/Orange alerts are     │
│    docked prominently at the top of the chat view.                         │
│ 4. Multilingual Fluidity: Seamless language toggling with instant re-render│
│    across English, Hindi, Bengali, Marathi, and Gujarati.                  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Screen Hierarchy & Visual Layout

```text
┌──────────────────────────────────────────────────────┐
│  [≡]  📍 Ahmedabad, GJ [▼]               [🗣️ EN|हि]  │  <- Header: Location & Language
├──────────────────────────────────────────────────────┤
│  [⚡ Auto ] [ General ] [ Farmer ] [ Research ] [Analyst]│  <- Brain Selector Pills
├──────────────────────────────────────────────────────┤
│  ⚠️ IMD Orange Alert: Heavy Rain in Dist. (Next 24h) │  <- Persistent Alert Banner (if active)
├──────────────────────────────────────────────────────┤
│                                                      │
│  [User Bubble]: "Should I irrigate cotton tomorrow?" │
│                                                      │
│  [WeatherGPT Farmer Card]:                           │
│  ┌────────────────────────────────────────────────┐  │
│  │ 🚫 ACTION: POSTPONE IRRIGATION                 │  │
│  │ 🌧️ Rain Expected: 35.0 mm (Prob: 82%)          │  │
│  │ 💧 Crop Water Demand: 4.6 mm/day (Flowering)   │  │
│  │ 📝 Rationale: Heavy rain exceeds crop demand.  │  │
│  └────────────────────────────────────────────────┘  │
│  "कल सूरत में भारी बारिश की संभावना के कारण कपास की   │
│   सिंचाई 2-3 दिनों के लिए स्थगित करें..."            │
│                                                      │
├──────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐   │
│  │ 💬 Ask about weather, farming, research... [🎤]│   │  <- Persistent Input & Voice Trigger
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

---

## 3. Specialized Adaptive UI Components

### 3.1 Brain Selector Pill Bar
Located directly under the top navigation header.
* **Auto Mode (Default):** Highlights dynamic AI routing.
* **Manual Brain Toggles:** `General`, `Farmer`, `Researcher`, `Analyst`. Tapping a manual pill locks the conversation into that domain mode until toggled back to Auto.

### 3.2 Dynamic Weather Card (`viz_card`)
Rendered for general weather queries.
* **Primary Metric:** Giant current temperature with weather condition glyph (e.g. `31°C 🌧️ Light Rain`).
* **Sub-metrics Row:** Min/Max range (`25°C / 33°C`), Precipitation Probability (`80%`), Humidity (`78%`), Wind Speed (`18 km/h`).
* **Hourly Forecast Scroller:** Horizontal carousel displaying the next 24 hours at 3-hour intervals.

### 3.3 Farmer Advisory Card (`viz_farmer_advisory`)
Rendered when the Farmer Brain emits agricultural guidance.
* **Action Badge:** High-contrast pill (`POSTPONE` in Amber, `IRRIGATE` in Blue, `WITHHOLD` in Red).
* **Agronomic Balance Grid:** Displays Reference $ET_0$, Crop Water Demand, and 48-Hour Forecast Rain.
* **Spray Suitability Indicator:** Green checkmark (`Suitable`) or Red warning icon (`Unsuitable - High Wind & Rain Risk`).

### 3.4 Researcher Interactive Chart & Table Card (`viz_research_chart`)
Rendered for climate and historical trends.
* **Time-Series Graph:** Zoomable line/bar chart displaying historical multi-year series with trendline overlays.
* **Statistical Badge:** Displays Mann-Kendall $\tau$, $p$-value, and Sen's slope ($\text{mm/year}$).
* **Action Button:** `[ 📥 Export CSV Dataset ]` triggers instant browser/mobile file download.

### 3.5 Analyst Spatial Risk Map Card (`viz_analyst_map`)
Rendered for hazard-exposure queries.
* **Embedded Interactive Map:** Powered by MapLibre GL Native with vector district tiles.
* **Hazard Overlay:** Colored semi-transparent polygons indicating IMD warning boundaries.
* **Exposure Table:** Bottom sheet detailing exposed population, district overlap percentage, and highway kilometers.

---

## 4. Conversation History Drawer & Saved Context

Tapping the hamburger menu `[≡]` slides in the session navigation drawer:
1. **New Conversation Button:** Clears active turn state and resets to default location.
2. **Saved Farm / Profile Card:** Displays active crop, soil, and farm location with a quick-edit sheet.
3. **Recent Conversation List:** Chronological history grouped by date (Today, Yesterday, Last 7 Days).
4. **Offline Mode Indicator:** Visual badge indicating when cached data is being served due to network loss.
