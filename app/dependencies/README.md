# Dependencies & Composition Root (`app/dependencies/`)

## 1. Purpose
Centralize construction and wiring of the WeatherGPT service graph so that no
business logic instantiates infrastructure directly, and tests can substitute
isolated pieces cleanly.

## 2. Responsibilities
- `container.py` — `AppContainer`: the composition root that builds, holds, and
  disposes all wired services.
- `providers.py` — small FastAPI `Depends` helpers used by routers.

## 3. Wired Services in AppContainer
| Service Provider | Source Component |
| :--- | :--- |
| `LLMProvider` | `app.llm.factory.get_llm_provider` |
| `ToolGateway` | `app.tools.gateway.ToolGateway` + 15 deterministic domain tools |
| `BrainOrchestrator` | `app.brains.orchestrator.BrainOrchestrator` + 4 domain brains |
| `ContextManager` | `app.context.manager.ContextManager` |
| `GroundingService` | `app.grounding.service.GroundingService` |
| `DatabaseService` | `app.db.service.DatabaseService` + async connection pool |

## 4. FastAPI Dependency Injection Usage
```python
from app.dependencies import get_tool_gateway, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/api/v1/...")
async def route(
    gateway: ToolGateway = Depends(get_tool_gateway),
    session: AsyncSession = Depends(get_db_session),
):
    ...
```

## 5. Lifecycle
`AppContainer` is built asynchronously during FastAPI lifespan startup (`app/core/lifespan.py`) and gracefully disposed on shutdown via `container.adispose()`.
