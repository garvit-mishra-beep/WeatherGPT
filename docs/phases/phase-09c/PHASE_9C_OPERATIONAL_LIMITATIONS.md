# PHASE 9C — OPERATIONAL LIMITATIONS & SCIENTIFIC BOUNDARIES

## 1. Scientific Boundaries

1. **Real-time Streaming Does Not Equal Empirical Calibration**:
   - Ingesting operational weather observations at 15-minute intervals does not make prototype road disruption or vulnerability fragility curves scientifically calibrated.
   - Consequence models remain prototype heuristics until calibrated with local post-disaster ground-truth damage assessments.
2. **Deterministic Gating vs Heuristics**:
   - The system strictly adheres to deterministic mathematical rules. An LLM is never invoked to infer or hallucinate missing sensor data, hazard states, or emergency directives.

---

## 2. Operational Limitations

1. **Polling Frequency Constraints**:
   - In the absence of server-push webhooks from national government portals, IMD CAP alerts rely on 15-minute bounded polling intervals. Emergency alerts issued in the interim have a maximum latency bounded by the polling cycle.
2. **Mobile Device Connectivity**:
   - In rural terrain with prolonged cellular outages, the mobile client remains in offline mode, relying on the last verified cached decision state.
3. **Sensor Density and Microclimates**:
   - Sparse automatic weather station (AWS) density in remote mountain ghats may fail to capture hyper-local cloudburst events; the system relies on radar/satellite blends when ground telemetry is absent.
