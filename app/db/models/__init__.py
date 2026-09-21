"""ORM models package for WeatherGPT.

Re-exports all database models so metadata is discovered cleanly by Alembic
and application repositories.
"""

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.db.models.farmer import FarmerPlot
from app.db.models.outbox import ProactiveNotificationOutbox, UserDeviceToken
from app.db.models.personalization import (
    DecisionHistoryRecord,
    DecisionOutcomeRecord,
    ForecastVerificationRecord,
    UserActionTrackingRecord,
    UserPreferencesRecord,
)
from app.db.models.evidence import (
    ClaimRecordDB,
    EvidenceLineageDB,
    EvidenceRecordDB,
    RuntimeEvidenceBundleDB,
    SourceRegistryRecord,
)
from app.db.models.decision import (
    DecisionAssessmentRecordDB,
    DecisionHistoryRecordDB,
    DecisionVerificationRecordDB,
)

__all__ = [
    "SpatialCountry",
    "SpatialState",
    "SpatialDistrict",
    "SpatialSubDistrict",
    "FarmerPlot",
    "ProactiveNotificationOutbox",
    "UserDeviceToken",
    "UserPreferencesRecord",
    "DecisionHistoryRecord",
    "UserActionTrackingRecord",
    "DecisionOutcomeRecord",
    "ForecastVerificationRecord",
    "SourceRegistryRecord",
    "EvidenceRecordDB",
    "EvidenceLineageDB",
    "ClaimRecordDB",
    "RuntimeEvidenceBundleDB",
    "DecisionAssessmentRecordDB",
    "DecisionHistoryRecordDB",
    "DecisionVerificationRecordDB",
]
