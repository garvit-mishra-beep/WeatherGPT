"""WeatherGPT Provider Circuit Breaker Engine.

Implements stateful, independent circuit breakers per external meteorological provider:
- CLOSED: Requests pass through normally. Consecutive failures increment failure counter.
- OPEN: Fast-fails immediately with ProviderCircuitOpenError, protecting upstream services and eliminating latency.
- HALF_OPEN: Following cooldown recovery window, allows a single controlled probe to verify provider recovery.
- Concurrency-safe using asyncio.Lock, eliminating probe race conditions.
"""

import asyncio
from enum import Enum
import logging
import time
from typing import Optional

from app.adapters.errors import ProviderCircuitOpenError

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """Discrete circuit breaker operational states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Thread-safe and async-safe circuit breaker for external data provider isolation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.01, float(recovery_timeout))

        self._state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0
        self._last_state_change: float = time.monotonic()
        self._half_open_in_flight: bool = False
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Current operational state (evaluates cooldown expiration)."""
        if self._state == CircuitBreakerState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                return CircuitBreakerState.HALF_OPEN
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    async def can_execute(self) -> bool:
        """Determines if a request to the provider is permitted to proceed.

        Returns:
            True if request is permitted.

        Raises:
            ProviderCircuitOpenError: If the circuit is OPEN or probing in HALF_OPEN.
        """
        async with self._lock:
            now = time.monotonic()

            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.OPEN:
                elapsed = now - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info(
                        "Circuit breaker for '%s' cooldown expired (%.1fs >= %.1fs); entering HALF_OPEN for controlled probe",
                        self.name,
                        elapsed,
                        self.recovery_timeout,
                    )
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._last_state_change = now
                    self._half_open_in_flight = True
                    return True
                else:
                    remaining = self.recovery_timeout - elapsed
                    raise ProviderCircuitOpenError(
                        f"Circuit breaker for provider '{self.name}' is OPEN (cooldown remaining: {remaining:.1f}s)",
                        provider=self.name,
                        retry_after_seconds=round(remaining, 1),
                    )

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_in_flight:
                    raise ProviderCircuitOpenError(
                        f"Circuit breaker for provider '{self.name}' is HALF_OPEN (probe request already in flight)",
                        provider=self.name,
                        retry_after_seconds=1.0,
                    )
                else:
                    self._half_open_in_flight = True
                    return True

        return False

    async def record_success(self) -> None:
        """Records a successful response from the provider."""
        async with self._lock:
            now = time.monotonic()
            if self._state == CircuitBreakerState.HALF_OPEN:
                logger.info(
                    "Probe request succeeded for provider '%s'; resetting circuit to CLOSED",
                    self.name,
                )
                self._state = CircuitBreakerState.CLOSED
                self._consecutive_failures = 0
                self._half_open_in_flight = False
                self._last_state_change = now
            elif self._state == CircuitBreakerState.CLOSED:
                self._consecutive_failures = 0

    async def record_failure(self, error: Optional[Exception] = None) -> None:
        """Records a failed response or timeout from the provider."""
        async with self._lock:
            now = time.monotonic()
            self._last_failure_time = now

            if self._state == CircuitBreakerState.HALF_OPEN:
                logger.warning(
                    "Probe request failed for provider '%s' (%s); re-opening circuit to OPEN for %.1fs cooldown",
                    self.name,
                    error or "unspecified error",
                    self.recovery_timeout,
                )
                self._state = CircuitBreakerState.OPEN
                self._half_open_in_flight = False
                self._last_state_change = now
            elif self._state == CircuitBreakerState.CLOSED:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.failure_threshold:
                    logger.warning(
                        "Provider '%s' exceeded consecutive failure threshold (%d/%d); tripping circuit to OPEN for %.1fs cooldown",
                        self.name,
                        self._consecutive_failures,
                        self.failure_threshold,
                        self.recovery_timeout,
                    )
                    self._state = CircuitBreakerState.OPEN
                    self._last_state_change = now

    def get_status(self) -> dict:
        """Returns snapshot of current circuit breaker metrics."""
        now = time.monotonic()
        remaining_cooldown = 0.0
        if self._state == CircuitBreakerState.OPEN:
            elapsed = now - self._last_failure_time
            remaining_cooldown = max(0.0, self.recovery_timeout - elapsed)

        return {
            "provider": self.name,
            "state": self._state.value,
            "consecutive_failures": self._consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
            "remaining_cooldown_seconds": round(remaining_cooldown, 2),
            "is_available": self._state != CircuitBreakerState.OPEN,
        }

    async def reset(self) -> None:
        """Manually reset the circuit breaker back to CLOSED state."""
        async with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._consecutive_failures = 0
            self._last_failure_time = 0.0
            self._half_open_in_flight = False
            self._last_state_change = time.monotonic()
