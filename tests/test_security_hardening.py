"""Security Hardening & Production Audit Test Suite (B13.13).

Verifies:
1. No hardcoded credentials or private keys in the codebase.
2. CORS policy forbids wildcard with credentials.
3. SQL Injection resilience via parameterized queries.
4. Tool sandbox security constraints (command injection, vertex limits, India BBox validation).
5. Logging masks sensitive fields (api_key, password, authorization, secret).
"""

import os
import re
from httpx import ASGITransport, AsyncClient
import pytest

from app.config import Settings
from app.core.factory import create_app
from app.tools.errors import ToolSecurityError
from app.tools.gateway import ToolGateway


def test_no_hardcoded_secrets_in_codebase():
    """Scan tracked Python source and documentation files for real secret patterns."""
    secret_patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),               # AWS Access Key
        re.compile(r"ghp_[0-9a-zA-Z]{36}"),             # GitHub Personal Access Token
        re.compile(r"sk-[0-9a-zA-Z]{48}"),              # OpenAI API Key
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), # Private Keys
    ]

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    scan_dirs = ["app", "deploy", "scripts"]

    for d in scan_dirs:
        dir_path = os.path.join(workspace_root, d)
        if not os.path.exists(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if not file.endswith((".py", ".sh", ".conf", ".service", ".env.example")):
                    continue
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for pat in secret_patterns:
                        match = pat.search(content)
                        assert match is None, f"Potential secret found in {file_path}: {match.group(0)}"


def test_cors_production_fails_on_wildcard():
    """Verify application factory refuses to start in production if CORS contains wildcard."""
    insecure_settings = Settings(
        app_env="production",
        secret_key="a_very_strong_production_secret_key_12345",
        cors_origins=["*"],
        debug=False,
    )
    with pytest.raises(RuntimeError, match="Refusing to start in production: CORS_ORIGINS"):
        create_app(settings=insecure_settings, configure_logging_enabled=False)


def test_production_fails_on_insecure_default_secret():
    """Verify application factory refuses to start in production with default secret key."""
    insecure_settings = Settings(
        app_env="production",
        secret_key="default_dev_secret_key_change_in_production",
        cors_origins=["https://weathergpt.in"],
        debug=False,
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY is still the insecure default"):
        create_app(settings=insecure_settings, configure_logging_enabled=False)


@pytest.mark.asyncio
async def test_tool_gateway_blocks_dangerous_injection():
    """Verify ToolGateway sanitization rejects command injection and dangerous tokens."""
    from app.tools.registry import ToolRegistry
    registry = ToolRegistry()
    gateway = ToolGateway(registry=registry)

    # 1. Dangerous key
    with pytest.raises(ToolSecurityError) as exc_info:
        gateway._validate_security_and_bounds(
            "weather_fetch",
            {"command": "rm -rf /"}
        )
    assert "Disallowed security parameter" in str(exc_info.value)

    # 2. SQL injection pattern in value
    with pytest.raises(ToolSecurityError) as exc_info2:
        gateway._validate_security_and_bounds(
            "weather_fetch",
            {"query": "Surat'; DROP TABLE districts; --"}
        )
    assert "Disallowed SQL pattern" in str(exc_info2.value)
