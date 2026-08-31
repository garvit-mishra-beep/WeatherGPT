"""FastAPI exception handlers for the WeatherGPT backend.

B1 establishes a single, consistent error surface that builds on the existing
RFC 7807 contract (``app.contracts.error.ProblemDetailRFC7807``). All HTTP error
responses produced by the backend pass through these handlers so that the
payload shape is stable, safe (no internal stack traces), and versionable.

Exception *class* definitions live in :mod:`app.core.errors`; this module only
registers the handlers that convert exceptions into responses.

Existing domain subsystems (``app.brains.errors``, ``app.tools.errors``,
``app.context.errors``, ``app.grounding.errors``, ...) define their own rich
exceptions; those are mapped here rather than duplicated.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.contracts.error import ProblemDetailRFC7807
from app.core.errors import (
    BackendError,
    ConflictError,
    InvalidRequestIdError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.request_id import get_request_id

logger = logging.getLogger(__name__)

_ERROR_URI_BASE = "https://weathergpt.in/errors"


_RETRYABLE_STATUSES = frozenset({408, 429, 502, 503, 504})


def _http_status_phrase(status_code: int) -> str:
    from http import HTTPStatus

    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


def _build_problem(
    *,
    title: str,
    status: int,
    detail: str,
    error_code: Optional[str],
    request: Request,
    retryable: Optional[bool] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    extra = extra or {}
    is_retryable = retryable if retryable is not None else (status in _RETRYABLE_STATUSES)
    req_id = get_request_id()

    problem = ProblemDetailRFC7807(
        type=f"{_ERROR_URI_BASE}/{error_code if error_code else 'GENERIC_ERROR'}",
        title=title,
        status=status,
        detail=detail,
        instance=str(request.url.path) if request else None,
        error_code=error_code,
        request_id=req_id,
        retryable=is_retryable,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    payload = problem.model_dump(exclude_none=True)
    if extra:
        payload["details"] = extra
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all backend exception handlers onto a FastAPI application instance."""

    @app.exception_handler(BackendError)
    async def _backend_error_handler(request: Request, exc: BackendError) -> JSONResponse:
        logger.error(
            "Backend error (request_id=%s, error_code=%s, status=%d): %s",
            get_request_id(),
            exc.error_code,
            exc.status_code,
            exc.detail,
        )
        return _build_problem(
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
            request=request,
            extra=exc.extra or None,
        )

    from app.brains.errors import BrainError, BrainNotFoundError, BrainExecutionError
    from app.router.errors import RouterError
    from app.adapters.errors import AdapterError, ProviderUnavailableError, ProviderTimeoutError
    from app.grounding.errors import GroundingError
    from app.llm.types import LLMProviderError, LLMTimeoutError
    from app.tools.errors import (
        ToolArgumentValidationError,
        ToolAuthorizationError,
        ToolExecutionError,
        ToolGatewayError,
        ToolSecurityError,
        ToolTimeoutError,
        UnknownToolError,
    )

    @app.exception_handler(BrainNotFoundError)
    async def _brain_not_found_handler(request: Request, exc: BrainNotFoundError) -> JSONResponse:
        return _build_problem(
            title="Brain Not Found",
            status=404,
            detail=exc.message,
            error_code=exc.error_code,
            request=request,
            retryable=False,
            extra=exc.details,
        )

    @app.exception_handler(BrainExecutionError)
    async def _brain_execution_error_handler(request: Request, exc: BrainExecutionError) -> JSONResponse:
        logger.error("Brain execution error (request_id=%s): %s", get_request_id(), exc.message)
        return _build_problem(
            title="Brain Execution Error",
            status=500,
            detail=exc.message,
            error_code=exc.error_code,
            request=request,
            retryable=False,
            extra=exc.details,
        )

    @app.exception_handler(BrainError)
    async def _brain_error_handler(request: Request, exc: BrainError) -> JSONResponse:
        logger.error("Brain domain error (request_id=%s): %s", get_request_id(), exc.message)
        return _build_problem(
            title="Brain Execution Error",
            status=500,
            detail=exc.message,
            error_code=exc.error_code,
            request=request,
            retryable=False,
            extra=exc.details,
        )

    @app.exception_handler(RouterError)
    async def _router_error_handler(request: Request, exc: RouterError) -> JSONResponse:
        logger.error("Router error (request_id=%s): %s", get_request_id(), str(exc))
        return _build_problem(
            title="Auto Router Error",
            status=502,
            detail="Failed to classify or route query to appropriate domain intelligence brain",
            error_code="ROUTER_ERROR",
            request=request,
            retryable=True,
        )

    @app.exception_handler(LLMTimeoutError)
    async def _llm_timeout_handler(request: Request, exc: LLMTimeoutError) -> JSONResponse:
        return _build_problem(
            title="LLM Inference Timeout",
            status=504,
            detail="The inference server timed out processing the reasoning request",
            error_code="LLM_TIMEOUT",
            request=request,
            retryable=True,
        )

    @app.exception_handler(LLMProviderError)
    async def _llm_provider_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        status_code = exc.status_code if exc.status_code and exc.status_code in {400, 422, 502, 503, 504} else 502
        return _build_problem(
            title="LLM Inference Error",
            status=status_code,
            detail="Inference backend is temporarily unavailable or returned an error",
            error_code="LLM_PROVIDER_ERROR",
            request=request,
            retryable=(status_code in _RETRYABLE_STATUSES),
        )

    @app.exception_handler(ToolTimeoutError)
    async def _tool_timeout_handler(request: Request, exc: ToolTimeoutError) -> JSONResponse:
        return _build_problem(
            title="Tool Timeout",
            status=504,
            detail=f"Tool '{exc.tool_name}' timed out after {exc.timeout_seconds}s",
            error_code="TOOL_TIMEOUT",
            request=request,
            retryable=True,
        )

    @app.exception_handler(ToolSecurityError)
    async def _tool_security_handler(request: Request, exc: ToolSecurityError) -> JSONResponse:
        return _build_problem(
            title="Tool Security Violation",
            status=403,
            detail=f"Security constraint violated: {exc.reason}",
            error_code="TOOL_SECURITY_ERROR",
            request=request,
            retryable=False,
        )

    @app.exception_handler(ToolAuthorizationError)
    async def _tool_auth_handler(request: Request, exc: ToolAuthorizationError) -> JSONResponse:
        return _build_problem(
            title="Tool Authorization Denied",
            status=403,
            detail=f"Brain '{exc.brain.value}' is not authorized to invoke tool '{exc.tool_name}'",
            error_code="TOOL_UNAUTHORIZED",
            request=request,
            retryable=False,
        )

    @app.exception_handler(ToolArgumentValidationError)
    async def _tool_arg_validation_handler(request: Request, exc: ToolArgumentValidationError) -> JSONResponse:
        return _build_problem(
            title="Tool Argument Validation Error",
            status=422,
            detail=f"Invalid arguments for tool '{exc.tool_name}': {exc.reason}",
            error_code="TOOL_ARGUMENT_ERROR",
            request=request,
            retryable=False,
        )

    @app.exception_handler(ProviderTimeoutError)
    async def _provider_timeout_handler(request: Request, exc: ProviderTimeoutError) -> JSONResponse:
        return _build_problem(
            title="Provider Timeout",
            status=504,
            detail="External meteorological provider timed out",
            error_code="PROVIDER_TIMEOUT",
            request=request,
            retryable=True,
        )

    @app.exception_handler(ProviderUnavailableError)
    async def _provider_unavailable_handler(request: Request, exc: ProviderUnavailableError) -> JSONResponse:
        return _build_problem(
            title="Provider Unavailable",
            status=503,
            detail="Configured meteorological providers are temporarily unavailable",
            error_code="PROVIDER_UNAVAILABLE",
            request=request,
            retryable=True,
        )

    @app.exception_handler(AdapterError)
    async def _adapter_error_handler(request: Request, exc: AdapterError) -> JSONResponse:
        return _build_problem(
            title="Weather Adapter Error",
            status=502,
            detail="Failed to retrieve or parse external weather provider payload",
            error_code="ADAPTER_ERROR",
            request=request,
            retryable=True,
        )

    @app.exception_handler(GroundingError)
    async def _grounding_error_handler(request: Request, exc: GroundingError) -> JSONResponse:
        return _build_problem(
            title="Grounding Validation Error",
            status=422,
            detail=str(exc),
            error_code="GROUNDING_ERROR",
            request=request,
            retryable=False,
        )

    from app.gis.spatial.errors import DatabaseUnavailableError as SpatialDBUnavailable, SpatialEngineError

    @app.exception_handler(SpatialDBUnavailable)
    async def _spatial_db_unavailable_handler(request: Request, exc: SpatialDBUnavailable) -> JSONResponse:
        return _build_problem(
            title="Spatial Database Unavailable",
            status=503,
            detail="Spatial database is temporarily unavailable",
            error_code="DATABASE_UNAVAILABLE",
            request=request,
            retryable=True,
            extra=exc.details,
        )

    @app.exception_handler(SpatialEngineError)
    async def _spatial_engine_error_handler(request: Request, exc: SpatialEngineError) -> JSONResponse:
        return _build_problem(
            title="Spatial Engine Error",
            status=500,
            detail=exc.message,
            error_code="SPATIAL_ERROR",
            request=request,
            retryable=False,
            extra=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        detail = "Request validation failed."
        if errors:
            detail = f"Request validation failed: {len(errors)} field error(s)."
            locs = [
                ".".join(str(part) for part in (err.get("loc") or ()))
                for err in errors
            ]
            detail = (
                f"{detail} Invalid fields: {', '.join(locs) if locs else 'see details'}."
            )
        logger.info(
            "Request validation error (request_id=%s): %s",
            get_request_id(),
            errors,
        )
        return _build_problem(
            title="Validation Error",
            status=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
            request=request,
            retryable=False,
            extra={"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        status_code = exc.status_code
        logger.info(
            "HTTP error (request_id=%s, status=%d): %s",
            get_request_id(),
            status_code,
            exc.detail,
        )
        return _build_problem(
            title=_http_status_phrase(status_code),
            status=status_code,
            detail=str(exc.detail) if exc.detail else _http_status_phrase(status_code),
            error_code=None,
            request=request,
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Unexpected exceptions are logged in full but exposed to clients as a
        # generic, safe message — never a raw stack trace or internal detail.
        logger.exception(
            "Unhandled exception (request_id=%s, path=%s): %s",
            get_request_id(),
            request.url.path,
            exc,
        )
        detail = "An unexpected internal error occurred."
        return _build_problem(
            title="Internal Server Error",
            status=500,
            detail=detail,
            error_code="INTERNAL_SERVER_ERROR",
            request=request,
            retryable=False,
        )


__all__ = [
    "BackendError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    "InvalidRequestIdError",
    "register_exception_handlers",
]
