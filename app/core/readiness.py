"""Pluggable readiness probing for the WeatherGPT backend.

B1 provides a *mechanism*, not fabricated health checks. ``ReadinessChecker`` runs
a set of registered :class:`ReadinessProbe` instances and aggregates them into a
structured readiness report.

At B1 only probes whose dependencies actually exist are registered by default
(the base application probe). Future subsystems register their own probes when
they are implemented:

  * B2  — ``DatabaseProbe`` (PostgreSQL/PostGIS)
  * B4  — ``GISProbe``
  * B5  — ``NWPProbe`` (GFS/ECMWF grid reachability)
  * weather ingest — ``WeatherProbe``
  * LLM  — ``LLMProbe`` (network reachability — intentionally *not* in /health)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeResult:
    name: str
    ok: bool
    detail: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReadinessProbe(Protocol):
    name: str

    async def check(self) -> ProbeResult:
        """Return a ProbeResult describing current availability."""
        ...


@dataclass
class ReadinessChecker:
    """Runs and aggregates registered readiness probes."""

    probes: List[ReadinessProbe] = field(default_factory=list)

    def register(self, probe: ReadinessProbe) -> None:
        if not getattr(probe, "name", None):
            raise ValueError("ReadinessProbe must expose a 'name' attribute.")
        self.probes.append(probe)

    def clear(self) -> None:
        self.probes.clear()

    @property
    def names(self) -> List[str]:
        return [p.name for p in self.probes]

    async def check_all(self) -> tuple[bool, List[ProbeResult]]:
        """Run every registered probe and return (ready, per-probe results)."""
        results: List[ProbeResult] = []
        for probe in self.probes:
            try:
                start = time.perf_counter()
                result = await probe.check()
                latency = (time.perf_counter() - start) * 1000.0
                results.append(
                    ProbeResult(
                        name=result.name,
                        ok=result.ok,
                        detail=result.detail,
                        latency_ms=round(latency, 3),
                        metadata=result.metadata,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - probe failure must not crash /ready
                logger.exception("Readiness probe '%s' failed: %s", probe.name, exc)
                results.append(ProbeResult(name=probe.name, ok=False, detail="probe failed"))
        ready = all(r.ok for r in results) if results else True
        return ready, results


@dataclass
class ApplicationProbe:
    """Base probe indicating the process is constructed and able to serve."""

    name: str = "application"

    async def check(self) -> ProbeResult:
        return ProbeResult(name=self.name, ok=True, detail="application process ready")
