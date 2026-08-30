"""WeatherGPT REST API layer.

Contains the versioned route modules (``api/v1``) that expose the backend.
Routers are centralized in :mod:`app.api.v1.router` and mounted by the
application factory under a single ``/api/<version>`` prefix.
"""
