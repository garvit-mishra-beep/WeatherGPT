# Dependencies & Composition Root (`app/dependencies/`)

## 1. Purpose
Centralize construction and wiring of the WeatherGPT service graph so that no
business logic instantiates infrastructure directly, and tests can substitute
isolated pieces cleanly.

## 2. Responsibilities
- `container.py` — `AppContainer`: the composition root that builds, holds, and
  disposes all wired services.
- `providers.py` — small FastAPI `Depends` helpers used by routers.

## 3. Wiring (B1)
| Provider | Existing source |
| :--- | :--- |
| `LLMProvider` | `app.llm.factory.get_llm_provider` |
| `ToolGateway` | `app.tools.gateway` + registered default tools + `ToolResultCache` |
| `BrainOrchestrator` | `app.brains.orchestrator` + 4 domain brains |
| `ContextManager` | `app.context.manager` |
| `GroundingService` | `app.grounding.service` |

Only **existing** classes and factories are reused — no fake implementations.

## 4. FastAPI Usage
```python
from app.dependencies import get_tool_gateway

@app.get("/...")
async def route(gateway: ToolGateway = Depends(get_tool_gateway)):
    ...
```

## 5. Lifecycle
`AppContainer` is built during FastAPI lifespan startup and disposed at shutdown
(see `app/core/lifespan.py`).

## 6. Extension
Later phases add `DatabaseService`, `WeatherService`, `GISService`, `NWPService`
to the container with matching `Depends` helpers in `providers.py`.

## 7. Testing
Covered in `tests/test_backend_foundation.py` (mock LLM provider under
`app_env="test"`).
