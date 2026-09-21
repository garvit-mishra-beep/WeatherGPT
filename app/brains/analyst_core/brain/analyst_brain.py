"""Main AnalystBrain facade for WeatherGPT."""

from typing import Optional, Dict, Any
from app.brains.analyst_core.models.schemas import Persona
from app.brains.analyst_core.models.analyst_result import AnalystResult
from app.brains.analyst_core.data.providers.base import DataProvider
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider
from app.brains.analyst_core.nlu.context_memory import ConversationMemory
from app.brains.analyst_core.brain.orchestrator import AnalystOrchestrator
from app.brains.analyst_core.llm.explainer import LLMExplainer


class AnalystBrain:
    """WeatherGPT Analyst Brain Facade.
    
    A high-assurance, deterministic weather intelligence and decision-support engine.
    
    Adheres to:
    RAW WEATHER/CLIMATE DATA -> VALIDATION -> ANALYSIS -> RISK ASSESSMENT ->
    PATTERN DETECTION -> IMPACT INTERPRETATION -> ACTIONABLE INSIGHT
    """

    def __init__(
        self,
        provider: Optional[DataProvider] = None,
        use_synthetic: bool = False,
        explainer: Optional[LLMExplainer] = None,
    ):
        if provider is not None:
            self.provider = provider
        elif use_synthetic:
            self.provider = SyntheticProvider()
        else:
            self.provider = RealDataProvider()

        self.explainer = explainer or LLMExplainer()
        self.sessions: Dict[str, ConversationMemory] = {}

    def _get_memory(self, session_id: str) -> ConversationMemory:
        """Retrieves or creates conversational memory for a session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory()
        return self.sessions[session_id]

    def analyze(
        self,
        query: str,
        persona: Persona = Persona.ANALYST,
        language: str = "en",
        session_id: str = "default",
        context: Optional[Any] = None,
    ) -> AnalystResult:
        """Executes full analytical pipeline on user weather query with optional AnalysisContext."""
        memory = self._get_memory(session_id)
        orchestrator = AnalystOrchestrator(
            data_provider=self.provider,
            memory=memory,
            explainer=self.explainer,
        )
        return orchestrator.process_query(
            user_query=query,
            persona=persona,
            language=language,
            context=context,
        )

    def reset_session(self, session_id: str = "default") -> None:
        """Clears conversational memory for a session."""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
