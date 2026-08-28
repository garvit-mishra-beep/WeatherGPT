"""Monotonic latency and metric tracking instrumentation for WeatherGPT."""

import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Dict, Generator, Optional

from app.performance.models import PerformanceMetrics


class PerformanceTracker:
    """Instruments request lifecycles using high-precision monotonic timers."""

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        self.start_time: float = time.perf_counter()
        self.stage_timings: Dict[str, float] = {}
        self.llm_calls: int = 0
        self.tool_calls: int = 0
        self.grounding_retries: int = 0
        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None
        self.total_tokens: Optional[int] = None

    @contextmanager
    def track_stage(self, stage_name: str) -> Generator[None, None, None]:
        """Synchronous context manager tracking stage duration in milliseconds."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.stage_timings[stage_name] = self.stage_timings.get(stage_name, 0.0) + duration_ms

    @asynccontextmanager
    async def track_async_stage(self, stage_name: str) -> AsyncGenerator[None, None]:
        """Asynchronous context manager tracking stage duration in milliseconds."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.stage_timings[stage_name] = self.stage_timings.get(stage_name, 0.0) + duration_ms

    def record_llm_call(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        """Increments LLM call counter and updates token counters."""
        self.llm_calls += 1
        if prompt_tokens or completion_tokens:
            self.input_tokens = (self.input_tokens or 0) + prompt_tokens
            self.output_tokens = (self.output_tokens or 0) + completion_tokens
            self.total_tokens = (self.total_tokens or 0) + prompt_tokens + completion_tokens

    def record_tool_calls(self, count: int = 1) -> None:
        """Increments tool invocation counter."""
        self.tool_calls += count

    def record_grounding_retry(self) -> None:
        """Increments grounding regeneration counter."""
        self.grounding_retries += 1

    def build_metrics(self) -> PerformanceMetrics:
        """Assembles cumulative metrics envelope using monotonic duration."""
        total_duration_ms = (time.perf_counter() - self.start_time) * 1000.0

        return PerformanceMetrics(
            request_id=self.request_id,
            total_latency_ms=round(total_duration_ms, 2),
            context_latency_ms=round(self.stage_timings.get("context", 0.0), 2),
            router_latency_ms=round(self.stage_timings.get("router", 0.0), 2),
            llm_latency_ms=round(self.stage_timings.get("llm", 0.0), 2),
            tool_latency_ms=round(self.stage_timings.get("tools", 0.0), 2),
            grounding_latency_ms=round(self.stage_timings.get("grounding", 0.0), 2),
            llm_calls_count=self.llm_calls,
            tool_calls_count=self.tool_calls,
            grounding_retries_count=self.grounding_retries,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            stage_breakdown={k: round(v, 2) for k, v in self.stage_timings.items()},
        )
