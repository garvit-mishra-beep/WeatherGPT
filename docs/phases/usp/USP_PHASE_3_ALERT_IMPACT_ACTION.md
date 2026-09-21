# USP Phase 3 — Official Alert → Hazard → Exposure → Impact → Decision → Action

**Document:** `docs/USP_PHASE_3_ALERT_IMPACT_ACTION.md`  
**Status:** Implemented & Verified  
**Authority:** [`AGENTS.md`](../AGENTS.md) | [`docs/01_PRD.md`](01_PRD.md) | [`docs/15_ERROR_GUARDRAILS.md`](15_ERROR_GUARDRAILS.md)  
**Test Suite:** [`tests/test_usp_phase3_alert_impact.py`](../tests/test_usp_phase3_alert_impact.py) (10/10 Passing)

---

## 1. Executive Summary & Objective

In Indian meteorological workflows, an official weather warning issued by the India Meteorological Department (IMD) or NDMA Sachet often creates uncertainty if not contextualized:
> *"What does this official weather warning mean for my exact location, and what should I do?"*

**Vayubodhak USP Phase 3** operationalizes official weather warnings into deterministic, spatial, actionable decisions without using non-deterministic LLMs. It establishes a deterministic pipeline:

$$\text{Official Alert} \longrightarrow \text{Hazard} \longrightarrow \text{Affected Area} \longrightarrow \text{Verified Exposure} \longrightarrow \text{Risk/Impact} \longrightarrow \text{Decision} \longrightarrow \text{NirnayCard} \longrightarrow \text{Action}$$

```
                ┌───────────────────────────────────┐
                │  Official Alert (IMD / Sachet)   │
                │    (Red / Orange / Yellow / Green) │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │      Hazard Identification        │
                │ (Cyclone, Heavy Rain, Heatwave)   │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │     Affected Area Geometry        │
                │ (CAP Polygons, WKT, District Name)│
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │    Verified Spatial Exposure      │
                │     INSIDE | BUFFER | OUTSIDE     │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │   Impact = 0.50H + 0.30E + 0.20V  │
                │  Hazard × Exposure × Vulnerability│
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │      Operational Decision         │
                │      NO_GO | POSTPONE | GO        │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │       NirnayCard & Ledger         │
                │  Suppressed / Shifted Action Wdw  │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │     Recommended Direct Action     │
                └───────────────────────────────────┘
```

---

## 2. Core Non-Negotiable Rules

1. **Deterministic Only:** No LLM, Ollama, Gemma, or external AI inference may alter, predict, or evaluate official warnings.
2. **Official Alert Immutability:** Official IMD warning levels (`Red`, `Orange`, `Yellow`, `Green`) are absolute legal and public safety facts. They cannot be upgraded, downgraded, or contradicted by GFS, ECMWF, or numerical heuristics.
3. **WRF Honesty Rule:** When high-resolution regional NWP (WRF) is not ingested or unavailable, the system explicitly reports `wrf: unavailable` without fabricating consensus.
4. **Bounding Exposure:** A user outside an alert polygon or district boundary must receive a clear distinction: they are acknowledged as safe from direct polygon impacts, yet alerted if they reside in the precautionary buffer zone ($\le 25\text{ km}$).

---

## 3. Spatial Exposure Evaluation Pipeline

The spatial engine `AlertImpactEngine` resolves spatial containment across three cascading layers:

### 3.1 Point-in-Polygon (Ray-Casting Algorithm)
When alerts provide CAP coordinate polygons or WKT geometries (`POLYGON`, `MULTIPOLYGON`), the engine tests whether the user's coordinate $(lon, lat)$ falls strictly within the polygon boundary using Jordan curve ray-casting:

```python
inside = False
p1x, p1y = ring[0]
for i in range(1, n + 1):
    p2x, p2y = ring[i % n]
    if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
        if p1y != p2y:
            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
        if p1x == p2x or x <= xinters:
            inside = not inside
    p1x, p1y = p2x, p2y
```

If the point is contained, the exposure state is immediately classified as `INSIDE` ($E = 10.0$, overlap = $100\%$).

### 3.2 Metric Distance Perimeter Buffering
If the point is outside the polygon, the engine projects the coordinate onto each polygon boundary line segment to compute the geodesic distance $d_{min}$ in kilometers:

$$t = \text{clamp}\left(-\frac{\vec{p}_1 \cdot (\vec{p}_2 - \vec{p}_1)}{\|\vec{p}_2 - \vec{p}_1\|^2}, 0.0, 1.0\right)$$
$$\vec{proj} = \vec{p}_1 + t(\vec{p}_2 - \vec{p}_1), \quad d_{min} = \|\vec{proj}\|$$

- If $d_{min} \le 25.0\text{ km} \implies$ `ExposureState.BUFFER` ($E = 5.0$).
- If $d_{min} > 25.0\text{ km} \implies$ `ExposureState.OUTSIDE` ($E = 0.0$).

### 3.3 Administrative Area Fallback
When explicit polygon geometries are absent from an alert (common in text-based IMD district bulletins), the engine evaluates semantic containment against the user's location hierarchy (`district`, `state`, `name`). If the user's district appears in the alert's `area_description`, the location is classified as `INSIDE`.

---

## 4. Hazard, Exposure, and Vulnerability ($H \times E \times V$) Scoring

The composite operational impact is quantified using the standardized meteorological risk formulation:

$$\text{Impact} = 0.50 \times H + 0.30 \times E + 0.20 \times V$$

### 4.1 Hazard Scoring ($H \in [0.0, 10.0]$)
- **Red Alert:** $H = 10.0$ (Extreme / Life-Threatening)
- **Orange Alert:** $H = 7.0$ (Severe / Disruptive)
- **Yellow Alert:** $H = 4.0$ (Moderate / Watch & Prepare)
- **Green Alert:** $H = 1.0$ (Low / Normalcy)

### 4.2 Exposure Scoring ($E \in [0.0, 10.0]$)
- **INSIDE:** $E = 10.0$
- **BUFFER:** $E = 5.0$
- **OUTSIDE:** $E = 0.0$

### 4.3 Vulnerability Scoring ($V \in [0.0, 10.0]$)
- Baseline agricultural/outdoor vulnerability: $V = 5.0$.
- High-vulnerability settings (flood plains, cyclone tracks): up to $8.0$.

### 4.4 Risk Category Classification
- **$\text{Impact} \ge 7.0$:** Critical / High Risk
- **$4.0 \le \text{Impact} < 7.0$:** Medium Risk
- **$\text{Impact} < 4.0$:** Low Risk

---

## 5. Operational Decision Matrix

| Official Warning | Spatial Exposure | Decision Verdict | Action Window Behavior | Recommended Action |
| :--- | :--- | :--- | :--- | :--- |
| **Red** | `INSIDE` | `NO_GO` | **Suppressed** (`unavailable`) | **TAKE ACTION (EMERGENCY)**: Suspend all operations immediately, seek structurally sound shelter, obey district directives. |
| **Red** | `BUFFER` | `POSTPONE` | **Shifted / Constrained** | **BE PREPARED**: Within 25 km of Red Alert zone; postpone field operations until alert expires. |
| **Red** | `OUTSIDE` | `GO` (w/ Caution) | **Calculated** | Alert active in distant region; monitor conditions. |
| **Orange** | `INSIDE` | `POSTPONE` | **Shifted** (Starts $\ge \text{Expiry}$) | **BE PREPARED**: Severe weather active. Reschedule operation to next safe window after alert expires. |
| **Orange** | `INSIDE` (No Post-Expiry Wdw) | `POSTPONE` | **Unavailable** (`no_valid_window`) | Hazardous weather persists past forecast horizon; no safe window available. |
| **Yellow** | `INSIDE` | `GO` / `CAUTION` | **Calculated** | **BE UPDATED**: Monitor local updates; proceed with appropriate safety margins. |
| **Green** | `INSIDE` / `OUTSIDE`| `GO` | **Calculated** | Normal weather conditions apply. |

---

## 6. Multi-Hazard Compounding Rule

When multiple alerts are simultaneously active for an administrative boundary or geographic coordinate:
1. **Red Dominates:** A Red alert unconditionally supersedes Orange, Yellow, and Green alerts.
2. **Orange Dominates Yellow/Green:** An Orange alert supersedes Yellow and Green alerts.
3. **Compound Description:** The primary alert title and prescribed action reference the compound nature (e.g., *Very Severe Cyclonic Storm + Heavy Rainfall*).

---

## 7. Verification & Golden Test Coverage

The implementation is verified via `tests/test_usp_phase3_alert_impact.py` containing 10 rigorous test cases:

1. `test_red_alert_inside_forces_no_go`: Verifies Red alert inside forces `NO_GO` and suppresses action window.
2. `test_red_alert_outside_location_proceed_with_caution`: Verifies user outside polygon is unblocked.
3. `test_orange_alert_inside_postpones_shifts_action_window`: Verifies Orange alert shifts action window to start after alert expiration.
4. `test_orange_alert_no_valid_window_after_expiry`: Verifies `POSTPONE` with `no_valid_window` when no suitable slot exists after alert expiry.
5. `test_yellow_alert_watch_and_caution`: Verifies Yellow alert keeps operation feasible while adding caution.
6. `test_green_alert_normal_go`: Verifies Green alert allows normal execution.
7. `test_multi_hazard_compounding_red_overrides_orange`: Verifies Red overrides simultaneous Orange.
8. `test_spatial_point_in_polygon_exact_containment`: Verifies exact ray-casting and segment distance buffer logic.
9. `test_hxexv_impact_calculation_formula`: Verifies mathematical integrity of $0.50H + 0.30E + 0.20V$.
10. `test_api_decisions_with_alert_impact_fixture`: Verifies end-to-end `POST /api/v1/decisions` returns complete NirnayCard with alert impact evidence.

Full suite execution: **28/28 passing** across USP Phase 1, Phase 2, and Phase 3.
