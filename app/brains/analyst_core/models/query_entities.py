"""Entity extraction and slot representation models for Analyst Brain."""

from datetime import date as DateType, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class TimeWindow(BaseModel):
    """Normalized time window for meteorological analysis."""
    start_time: datetime
    end_time: datetime
    period_label: str = "custom"
    is_current: bool = False
    is_forecast: bool = False
    is_historical: bool = False


class QueryEntities(BaseModel):
    """Extracted meteorological, geographic, temporal, and operational query slots."""
    raw_query: str = ""
    location: Optional[str] = None
    comparison_location: Optional[str] = None
    date: Optional[DateType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_period: str = "current"
    forecast_horizon_hours: Optional[int] = None
    weather_variable: Optional[str] = None
    weather_event: Optional[str] = None
    threshold: Optional[float] = None
    comparison_period: Optional[str] = None
    period_a_dates: Optional[Tuple[DateType, DateType]] = None
    period_b_dates: Optional[Tuple[DateType, DateType]] = None
    period_a_label: Optional[str] = None
    period_b_label: Optional[str] = None
    user_objective: Optional[str] = None
    requested_decision: Optional[str] = None
    risk_category: Optional[str] = None
    relevant_sector: Optional[str] = None
    scenario_condition: Optional[str] = None
    language: str = "en"
    missing_slots: List[str] = Field(default_factory=list)
    is_clarification_needed: bool = False
    clarification_question: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
