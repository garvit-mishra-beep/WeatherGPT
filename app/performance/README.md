# Performance & Latency Layer (`app/performance/`)

## 1. Purpose
Provides high-efficiency execution primitives, monotonic latency tracking, HTTP connection pooling, and deterministic tool result caching.

## 2. Responsibilities
- Track stage-by-stage latency (Router, Tool Loop, Grounding, Total Duration) using monotonic clocks.
- Deduplicate identical deterministic tool invocations within short time windows via `ToolResultCache`.
- Maintain persistent HTTP connection pools to avoid per-request TCP handshakes.
- Coordinate concurrent tool executions via `asyncio.gather()`.

## 3. Important Files
- `tracker.py`: `PerformanceTracker` and `PerformanceMetrics` collecting execution durations.
- `cache.py`: In-memory `ToolResultCache` with TTL expiration and memory eviction bounds.

## 4. Measured Benchmarks
- Full test suite execution: **184 tests in ~1.4 seconds** on Python 3.14.
- In-memory cache roundtrip: $< 0.1\text{ ms}$.
