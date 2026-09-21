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


@dataclass
class ProviderHealthProbe:
    """Aggregated probe reporting meteorological and air quality provider circuit health without failing overall readiness."""

    name: str = "providers"
    weather_manager: Optional[Any] = None

    async def check(self) -> ProbeResult:
        if self.weather_manager is None:
            return ProbeResult(name=self.name, ok=True, detail="no provider manager bound")

        circuit_status = self.weather_manager.get_circuit_status()
        degraded = [p for p, status in circuit_status.items() if status.get("state") == "OPEN"]
        detail = "all provider circuits normal" if not degraded else f"degraded provider circuits: {', '.join(degraded)}"

        return ProbeResult(
            name=self.name,
            ok=True,  # Application readiness does not fail when external optional upstream is down
            detail=detail,
            metadata={
                "circuits": circuit_status,
                "degraded_count": len(degraded),
            },
        )


@dataclass
class OllamaProbe:
    """Readiness probe reporting local Ollama LLM provider availability and model status."""

    name: str = "ollama"
    settings: Optional[Any] = None
    provider: Optional[Any] = None

    async def check(self) -> ProbeResult:
        if self.settings and not getattr(self.settings, "ollama_enabled", False) and getattr(self.settings, "llm_provider_type", "") != "ollama":
            return ProbeResult(
                name=self.name,
                ok=True,
                detail="Ollama disabled (using production LLM provider)",
                metadata={"status": "DISABLED", "ollama_enabled": False},
            )

        if self.provider is None:
            from app.llm.providers.ollama_provider import OllamaProvider
            base_url = getattr(self.settings, "ollama_base_url", "http://127.0.0.1:11434") if self.settings else "http://127.0.0.1:11434"
            model_name = getattr(self.settings, "ollama_model", "qwen2.5:1.5b-instruct") if self.settings else "qwen2.5:1.5b-instruct"
            timeout = min(float(getattr(self.settings, "ollama_timeout_seconds", 5.0) if self.settings else 5.0), 5.0)
            self.provider = OllamaProvider(base_url=base_url, model_name=model_name, timeout_seconds=timeout)

        is_healthy = await self.provider.check_health()
        if not is_healthy:
            return ProbeResult(
                name=self.name,
                ok=False,
                detail=f"Ollama server unreachable at {self.provider.base_url}",
                metadata={
                    "status": "UNAVAILABLE",
                    "base_url": self.provider.base_url,
                    "model": self.provider.model_name,
                },
            )

        model_ok = await self.provider.check_model_available()
        if not model_ok:
            available = await self.provider.list_available_models()
            return ProbeResult(
                name=self.name,
                ok=False,
                detail=f"Ollama reachable but configured model '{self.provider.model_name}' is not pulled. Available: {available}",
                metadata={
                    "status": "UNAVAILABLE",
                    "base_url": self.provider.base_url,
                    "configured_model": self.provider.model_name,
                    "available_models": available,
                },
            )

        return ProbeResult(
            name=self.name,
            ok=True,
            detail=f"Ollama AVAILABLE with model '{self.provider.model_name}'",
            metadata={
                "status": "AVAILABLE",
                "base_url": self.provider.base_url,
                "model": self.provider.model_name,
            },
        )

