"""VAYUBODHAK Showcase & Demonstration Module.

Provides deterministic showcase datasets and scenario runner for reproducible,
high-fidelity video demonstrations and offline/failure resilience validation.
"""

from app.showcase.runner import ShowcaseScenarioRunner, showcase_runner

__all__ = ["ShowcaseScenarioRunner", "showcase_runner"]
