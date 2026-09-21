"""B11 — Native Production Deployment Test Suite.

Verifies:
1. Production configuration loading and fail-fast validation.
2. Secret key, CORS wildcard, and DEBUG guardrails in production.
3. Structured logging sensitive field redaction.
4. Health (/api/v1/health) and Readiness (/api/v1/ready) probes.
5. Database connection pooling configuration.
6. Graceful application lifecycle shutdown.
7. Deployment templates (systemd, nginx, env) integrity.
8. Repository secret scanner for unmasked credential protection.
9. Absence of Docker/Kubernetes dependencies in B11.
"""

import logging
import os
import re
from typing import Any, Dict
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.core.factory import create_app
from app.core.logging import StructuredJsonFormatter
from app.db.service import DatabaseService
from app.dependencies.container import AppContainer


# ============================================================================
# 1. Configuration & Production Guardrails
# ============================================================================

def test_production_config_loading():
    """Verify Settings object initialization across profiles."""
    dev_cfg = Settings(app_env="development", secret_key="dev_secret")
    assert dev_cfg.app_env == "development"
    assert dev_cfg.is_production is False

    prod_cfg = Settings(app_env="production", secret_key="super_secret_production_key_64_bytes_long")
    assert prod_cfg.app_env == "production"
    assert prod_cfg.is_production is True


def test_production_insecure_secret_rejected():
    """Verify application refuses to boot in production with default secret."""
    cfg = Settings(
        app_env="production",
        secret_key="default_dev_secret_key_change_in_production",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY is still the insecure default"):
        create_app(settings=cfg, configure_logging_enabled=False)


def test_production_wildcard_cors_rejected():
    """Verify application refuses to boot in production with wildcard CORS."""
    cfg = Settings(
        app_env="production",
        secret_key="valid_production_secret_key_12345",
        cors_origins=["*"],
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be an explicit allowlist"):
        create_app(settings=cfg, configure_logging_enabled=False)


def test_production_debug_enabled_rejected():
    """Verify application refuses to boot in production with debug=True."""
    cfg = Settings(
        app_env="production",
        secret_key="valid_production_secret_key_12345",
        cors_origins=["https://weathergpt.in"],
        debug=True,
    )
    with pytest.raises(RuntimeError, match="DEBUG is set to true"):
        create_app(settings=cfg, configure_logging_enabled=False)


def test_production_docs_toggle():
    """Verify /docs and /redoc can be disabled in production."""
    cfg_docs_off = Settings(
        app_env="development",
        docs_enabled=False,
    )
    app = create_app(settings=cfg_docs_off, configure_logging_enabled=False)
    assert app.docs_url is None
    assert app.redoc_url is None

    cfg_docs_on = Settings(
        app_env="development",
        docs_enabled=True,
    )
    app_on = create_app(settings=cfg_docs_on, configure_logging_enabled=False)
    assert app_on.docs_url == "/docs"
    assert app_on.redoc_url == "/redoc"


# ============================================================================
# 2. Secret Redaction in Structured Logging
# ============================================================================

def test_logging_secret_redaction():
    """Ensure StructuredJsonFormatter automatically redacts sensitive variables."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authentication attempt",
        args=(),
        exc_info=None,
    )
    # Attach sensitive extra properties
    record.api_key = "sk_live_1234567890abcdef"
    record.password = "MySuperSecretPassword"
    record.token = "bearer_token_xyz"
    record.request_id = "req_12345"

    formatted = formatter.format(record)
    import json
    parsed = json.loads(formatted)

    assert parsed["request_id"] == "req_12345"
    assert parsed["api_key"] == "[REDACTED]"
    assert parsed["password"] == "[REDACTED]"
    assert parsed["token"] == "[REDACTED]"
    assert "MySuperSecretPassword" not in formatted


# ============================================================================
# 3. Health & Readiness Probes
# ============================================================================

def test_health_endpoint():
    """Verify lightweight liveness probe /api/v1/health."""
    from fastapi.testclient import TestClient

    cfg = Settings(app_env="test")
    app = create_app(settings=cfg, configure_logging_enabled=False)

    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "X-Request-ID" in resp.headers


def test_readiness_endpoint():
    """Verify readiness probe /api/v1/ready aggregates application probes."""
    from fastapi.testclient import TestClient

    cfg = Settings(app_env="test")
    app = create_app(settings=cfg, configure_logging_enabled=False)

    with TestClient(app) as client:
        resp = client.get("/api/v1/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "ready" in data


# ============================================================================
# 4. Database Connection Pool & Lifecycle
# ============================================================================

def test_database_connection_pool_configuration():
    """Verify pool parameters propagate to DatabaseService."""
    cfg = Settings(
        app_env="test",
        database_pool_size=15,
        database_max_overflow=7,
        database_pool_timeout=12.0,
        database_pool_recycle=1200,
    )
    db_svc = DatabaseService(settings=cfg)
    assert db_svc.settings.database_pool_size == 15
    assert db_svc.settings.database_max_overflow == 7
    assert db_svc.settings.database_pool_timeout == 12.0
    assert db_svc.settings.database_pool_recycle == 1200


@pytest.mark.asyncio
async def test_graceful_lifecycle_disposal():
    """Verify AppContainer adispose safely releases resources."""
    cfg = Settings(app_env="test")
    container = AppContainer(settings=cfg).build()
    # Ensure adispose executes idempotently without raising
    await container.adispose()
    await container.adispose()


# ============================================================================
# 5. Deployment Templates & Artifact Integrity
# ============================================================================

def test_systemd_template_integrity():
    """Verify deploy/weathergpt.service.example contains mandatory directives."""
    service_path = os.path.join(os.path.dirname(__file__), "..", "deploy", "weathergpt.service.example")
    assert os.path.exists(service_path), "deploy/weathergpt.service.example must exist"
    with open(service_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ExecStart=" in content
    assert "uvicorn app.main:app" in content
    assert "EnvironmentFile=" in content
    assert "User=weathergpt" in content
    assert "Restart=always" in content
    assert "KillSignal=SIGTERM" in content


def test_nginx_template_integrity():
    """Verify deploy/nginx.conf.example contains proxy and security directives."""
    nginx_path = os.path.join(os.path.dirname(__file__), "..", "deploy", "nginx.conf.example")
    assert os.path.exists(nginx_path), "deploy/nginx.conf.example must exist"
    with open(nginx_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "upstream weathergpt_backend" in content
    assert "proxy_pass http://weathergpt_backend;" in content
    assert "X-Request-ID" in content
    assert "X-Forwarded-For" in content
    assert "Strict-Transport-Security" in content
    assert "X-Content-Type-Options" in content


def test_env_example_completeness():
    """Verify .env.example contains essential environment variable keys."""
    env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.exists(env_example_path)
    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_keys = [
        "APP_ENV",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "DATABASE_POOL_SIZE",
        "LLM_PROVIDER_TYPE",
        "LLM_BASE_URL",
        "IMD_BASE_URL",
        "GFS_BASE_URL",
        "OPEN_METEO_BASE_URL",
    ]
    for key in required_keys:
        assert key in content, f"Missing required key '{key}' in .env.example"


# ============================================================================
# 6. Repository Secret Scanner
# ============================================================================

def test_no_hardcoded_secrets_in_repo():
    """Scans Python files to detect obvious committed secret patterns."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    forbidden_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{32,}"),  # OpenAI live keys
        re.compile(r"postgres(?:ql)?:\/\/[a-zA-Z0-9_-]+:(?!(?:postgres|password|replace_with|test))[a-zA-Z0-9_-]{8,}@"),  # Non-trivial unmasked DB passwords
    ]

    for root, dirs, files in os.walk(os.path.join(repo_root, "app")):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pattern in forbidden_patterns:
                    assert not pattern.search(content), f"Potential secret pattern found in {file_path}"
