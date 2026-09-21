"""Multi-turn conversation context and slot tracking for Analyst Brain."""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.brains.analyst_core.models.schemas import QueryCategory, HazardType, RiskLevel
from app.brains.analyst_core.models.query_entities import QueryEntities


class TurnRecord(BaseModel):
    """Record of a single conversation turn."""
    turn_index: int
    user_query: str
    category: QueryCategory
    entities: QueryEntities
    risk_level: Optional[RiskLevel] = None
    hazards: List[HazardType] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationMemory:
    """Tracks conversation context across multiple turns."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.turns: List[TurnRecord] = []
        self.active_location: Optional[str] = None
        self.active_comparison_location: Optional[str] = None
        self.active_date: Optional[date] = None
        self.active_time_period: str = "current"
        self.active_hazard: Optional[HazardType] = None
        self.active_objective: Optional[str] = None
        self.active_variable: Optional[str] = None
        self.active_sector: Optional[str] = None
        self.last_analysis_result: Optional[Dict[str, Any]] = None

    def update(
        self,
        user_query: str,
        category: QueryCategory,
        entities: QueryEntities,
        risk_level: Optional[RiskLevel] = None,
        hazards: Optional[List[HazardType]] = None,
    ) -> None:
        """Updates active memory with the latest user query and resolved entities."""
        if entities.location:
            self.active_location = entities.location
        if entities.comparison_location:
            self.active_comparison_location = entities.comparison_location
        if entities.date:
            self.active_date = entities.date
        if entities.time_period:
            self.active_time_period = entities.time_period
        if entities.user_objective:
            self.active_objective = entities.user_objective
        if entities.weather_variable:
            self.active_variable = entities.weather_variable
        if entities.relevant_sector:
            self.active_sector = entities.relevant_sector
        if hazards:
            self.active_hazard = hazards[0]

        turn = TurnRecord(
            turn_index=len(self.turns) + 1,
            user_query=user_query,
            category=category,
            entities=entities,
            risk_level=risk_level,
            hazards=hazards or [],
        )
        self.turns.append(turn)
        if len(self.turns) > self.max_history:
            self.turns.pop(0)

    def resolve_context(self, entities: QueryEntities) -> QueryEntities:
        """Fills missing slots from active conversational memory."""
        if not entities.location and self.active_location:
            entities.location = self.active_location
            entities.metadata["location_inherited_from_context"] = True

        if not entities.comparison_location and self.active_comparison_location:
            entities.comparison_location = self.active_comparison_location

        if not entities.date and self.active_date and entities.time_period == "current":
            # If the user previously specified a date (e.g. tomorrow) and asks a follow-up
            if self.active_time_period != "current":
                entities.date = self.active_date
                entities.time_period = self.active_time_period

        if not entities.user_objective and self.active_objective:
            entities.user_objective = self.active_objective

        if not entities.weather_variable and self.active_variable:
            entities.weather_variable = self.active_variable

        if not entities.relevant_sector and self.active_sector:
            entities.relevant_sector = self.active_sector

        return entities

    def clear(self) -> None:
        """Resets conversational memory."""
        self.turns.clear()
        self.active_location = None
        self.active_comparison_location = None
        self.active_date = None
        self.active_time_period = "current"
        self.active_hazard = None
        self.active_objective = None
        self.active_variable = None
        self.active_sector = None
        self.last_analysis_result = None
