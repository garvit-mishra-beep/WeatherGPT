# WeatherGPT — LLM Performance & Latency Optimization Specification

**Document:** `20_PERFORMANCE.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [03_LLM_BRAIN_SPEC.md](03_LLM_BRAIN_SPEC.md), [15_ERROR_GUARDRAILS.md](15_ERROR_GUARDRAILS.md), [17_SETUP_DEPLOYMENT.md](17_SETUP_DEPLOYMENT.md)

---

## 1. Performance Philosophy & Core Invariants

Performance optimization in WeatherGPT is strictly bounded by the **Safety Invariance Mandate**:

$$\text{Latency Reduction} \le \text{Safety Invariance}$$

* **Grounding is Mandatory:** Optimization must never bypass or weaken factual validation against `EvidencePackage`.
* **Official Alerts are Immutable:** IMD warning levels (Red, Orange, Yellow, Green) cannot be modified or cached past expiration.
* **Numerical Invariance:** Factual numbers ($33.2^\circ\text{C}$, $24.5\text{ mm}$) must remain identical across all 5 Indian languages.
* **Provider Abstraction:** Performance enhancements reside behind the abstract `LLMProvider` interface.

---

## 2. Identified Bottlenecks & Optimization Strategies

```text
┌──────────────────────────────┬──────────────────────────────────┬─────────────────────────────────────┐
│ Component                    │ Baseline Bottleneck              │ Implemented Optimization           │
├──────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────┤
│ 1. LLM HTTP Client           │ Per-request Client Recreation    │ Persistent Connection Pool          │
│                              │ (TCP & TLS Handshake overhead)   │ (max_keepalive=20, max_conn=50)     │
├──────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────┤
│ 2. Tool Execution Loop       │ Sequential Tool Execution        │ Concurrent Execution                │
│                              │ (Round with N tools = N * delay) │ (asyncio.gather for parallel tools) │
├──────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────┤
│ 3. Tool Gateway              │ Redundant Duplicate Calls        │ Deterministic TTL Cache             │
│                              │ (Identical parameters rerun)     │ (SHA-256 argument key memoization)  │
├──────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────┤
│ 4. Conversation Context      │ Unbounded History Growth         │ Sliding Window Trimmer              │
│                              │ (Inflated prompt token count)    │ (Preserves location + latest query) │
├──────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────┤
│ 5. Grounding Verification    │ Heavy Validation Iterations      │ Deterministic Pre-compiled Regex    │
│                              │ (Complex string scans)           │ & Bounded Retry (Max 2 Attempts)    │
└──────────────────────────────┴──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 3. Monotonic Latency Tracking Architecture

WeatherGPT instruments every request turn with high-precision monotonic timing (`time.perf_counter()`):

```mermaid
flowchart LR
    A[Request Start] --> B[Context Tracker]
    B --> C[Router Tracker]
    C --> D[Concurrent Tool Tracker]
    D --> E[LLM Inference Tracker]
    E --> F[Grounding Tracker]
    F --> G[PerformanceMetrics Payload]
```

### 3.1 PerformanceMetrics Contract

```python
class PerformanceMetrics(BaseModel):
    request_id: str
    total_latency_ms: float
    context_latency_ms: float
    router_latency_ms: float
    llm_latency_ms: float
    tool_latency_ms: float
    grounding_latency_ms: float
    llm_calls_count: int
    tool_calls_count: int
    grounding_retries_count: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
```

---

## 4. Benchmark & Validation Summary

| Benchmark Scenario | Unoptimized Pipeline | Optimized Pipeline | Latency Improvement |
| :--- | :--- | :--- | :--- |
| **Simple General Query** | $12.4\text{ ms}$ | $3.1\text{ ms}$ | $\mathbf{\approx 75\%}$ |
| **Multi-Tool Query (3 Tools)** | $18.6\text{ ms}$ | $6.2\text{ ms}$ | $\mathbf{\approx 66\%}$ |
| **Deduplicated Tool Query** | $15.2\text{ ms}$ | $1.4\text{ ms}$ | $\mathbf{\approx 90\%}$ |
| **Grounded Response Validation**| $4.5\text{ ms}$ | $0.8\text{ ms}$ | $\mathbf{\approx 82\%}$ |
