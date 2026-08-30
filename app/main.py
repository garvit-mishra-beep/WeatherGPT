"""WeatherGPT FastAPI application entrypoint.

This module wires the application factory into an ASGI ``app`` object for the
server (e.g. ``uvicorn app.main:app``). All application construction — metadata,
middleware, handlers, routers, and lifecycle — is delegated to
:func:`app.core.factory.create_app`. No business logic lives here.
"""

from app.config import settings
from app.core.factory import create_app

app = create_app(settings=settings)

__all__ = ["app"]
