# VAYUBODHAK Data Repository

**Directory:** `data/`  
**Purpose:** Storage for static agronomic reference parameters, canonical event/evidence schemas, and the controlled showcase dataset.

---

## Directory Organization

```text
data/
├── reference/      # Static agronomic lookup tables, crop coefficients (Kc), spatial boundaries
├── schemas/        # Canonical JSON schemas for OperationalEvent, Evidence, and DecisionRevision
└── showcase/       # Controlled scenario fixtures for deterministic product demonstrations
    ├── scenario_manifest.json
    ├── weather_initial.json
    ├── weather_rain_increase.json
    ├── warning_update.json
    ├── exposure_snapshot.json
    └── vulnerability_snapshot.json
```

---

## Data Policy & Privacy
* No classified, personal, or private user telemetry is stored in this repository.
* For full data classification and licensing policies, refer to [`docs/data/DATA_CLASSIFICATION.md`](../docs/data/DATA_CLASSIFICATION.md) and [`docs/data/DATA_PROVENANCE.md`](../docs/data/DATA_PROVENANCE.md).
