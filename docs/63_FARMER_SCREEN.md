# 63. Farmer Screen — Milestone P6.8 Specification & Verification

**Document:** `docs/63_FARMER_SCREEN.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.8 — Farmer Advisory Screen Visual & Functional Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint (Screen: किसान सलाह / Farmer Advisory)  
**Primary Authorities:** [`docs/01_PRD.md`](docs/01_PRD.md), [`docs/11_ANALYTICS_ENGINE.md`](docs/11_ANALYTICS_ENGINE.md), [`docs/14_MOBILE_UI_SPEC.md`](docs/14_MOBILE_UI_SPEC.md), [`docs/58_ANDROID_API_INTEGRATION.md`](docs/58_ANDROID_API_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P6.8** delivers the complete visual and functional implementation of the **FARMER SCREEN (किसान सलाह)** in Android Jetpack Compose, consuming deterministic FAO-56 Penman-Monteith crop water balance and meteorological spray window analytics from the FastAPI backend services (`GET /api/v1/farmer/irrigation-advisory` and `GET /api/v1/farmer/spray-window`).

```
┌─────────────────────────────────────────────────────────────┐
│ 📍 Jhansi, Uttar Pradesh                                    │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🌾 फसल एवं खेत विवरण (Crop Profile)                    │ │
│ │ मुख्य फसल: [ गेहूं (Wheat) ] [ धान ] [ कपास ] [ सरसों ] │ │
│ │ वृद्धि अवस्था: [ बुवाई ] [ वानस्पतिक (Active) ] [ फूल ]  │ │
│ │ मिट्टी: [ दोमट मिट्टी (Loam) ] [ काली मिट्टी ]           │ │
│ │ खेत का क्षेत्रफल: [ 2.5 Hectares ]       [ लागू करें ]   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 💧 सिंचाई आवश्यकता                 [ Urgency: High ]    │ │
│ │ कार्रवाई: IRRIGATE                                       │ │
│ │ फसल वाष्पोत्सर्जन (ETc) उपलब्ध मृदा नमी से अधिक है।       │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ ET₀: 4.2 mm/day │ Deficit: -20.0 mm │ Rain: 0.0 mm  │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🛡️ कीटनाशक छिड़काव             [ ✅ अनुकूल (Suitable) ] │ │
│ │ मौसम स्थितियां कीटनाशक छिड़काव के लिए अनुकूल हैं।       │ │
│ │ हवा गति: ✅ अनुकूल (12 km/h) • वर्षा संभावना: ✅ अनुकूल  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Real API Endpoint Mapping

| Section | Backend API Endpoint | Android Domain Model | Displayed Fields |
|---|---|---|---|
| **Irrigation Advisory** | `GET /api/v1/farmer/irrigation-advisory` | `IrrigationAdvisory` | `action`, `urgency`, `rationale`, `metrics.referenceEt0MmDay`, `metrics.cropKc`, `metrics.dailyWaterDemandMm`, `metrics.forecastRainfall48hMm`, `metrics.netDeficitMm` |
| **Spray Suitability** | `GET /api/v1/farmer/spray-window` | `SpraySuitability` | `isSuitable`, `conditionLevel`, `recommendation`, `windSuitable`, `rainProbabilitySuitable`, `calculationMethod` |

---

## 3. Profile Validation & Resilience

1. **Crop & Soil Parameters**:
   - Supports Wheat, Rice, Cotton, Mustard, Sugarcane, Maize across Sowing, Vegetative, Flowering, and Maturity growth stages.
   - Soil textures: Alluvial Loam, Black Cotton, Red Sandy, and Clay.
2. **Input Validation**:
   - Validates positive numerical values for field acreage with contextual error cues.
3. **FAO-56 Scientific Precision**:
   - Evaluates reference evapotranspiration $ET_0$, crop coefficient $K_c$, crop demand $ET_c = K_c \times ET_0$, 48-hour rainfall forecast, and net root zone water deficit.
4. **Lifecycle & State Handling**:
   - Full support for `LoadingState`, `ErrorState`, offline detection, and immediate reactive reload upon location or crop profile adjustments.

---

## 4. Verification & Testing

- **Tests:** 127/127 unit tests passing cleanly.
- **Scenarios:** `farmerProfileViewModel_loadsIrrigationAndSprayAdvisories`, `farmerProfileViewModel_cropSelectionAndValidation`.
