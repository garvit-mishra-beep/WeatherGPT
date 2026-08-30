"""WeatherGPT Production Configuration & Readiness Verification Tool.

Validates environment variables, secret masking, database connectivity,
and PostGIS extension status without revealing sensitive credentials.

Usage:
    python scripts/verify_production_config.py [--env-file .env]
"""

import argparse
import asyncio
import os
import sys
from typing import List, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import Settings
from app.db.service import DatabaseService


def mask_url_password(url: str) -> str:
    """Masks password components from database/API URLs."""
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        user_info, host_info = rest.split("@", 1)
        user = user_info.split(":", 1)[0]
        return f"{prefix}://{user}:[REDACTED]@{host_info}"
    return url


async def verify_configuration(settings: Settings) -> Tuple[bool, List[str]]:
    """Runs verification checks against Settings and database."""
    issues: List[str] = []
    is_prod = settings.app_env == "production"

    print("=====================================================================")
    print(f"WeatherGPT Configuration Audit (Profile: {settings.app_env.upper()})")
    print("=====================================================================")
    print(f"App Name:             {settings.app_name}")
    print(f"API Version:          {settings.api_version}")
    print(f"Host & Port:          {settings.host}:{settings.port}")
    print(f"Log Level:            {settings.log_level}")
    print(f"Database URL:         {mask_url_password(settings.database_url)}")
    print(f"DB Pool Size:         {settings.database_pool_size} (Max Overflow: {settings.database_max_overflow})")
    print(f"CORS Origins:         {settings.cors_origins}")
    print(f"Interactive Docs:     {'Enabled' if settings.docs_enabled else 'Disabled'}")
    print(f"LLM Provider:         {settings.llm_provider_type} ({settings.llm_model_name})")
    print("---------------------------------------------------------------------")

    # 1. Secret Key Check
    if is_prod and "change_in_production" in settings.secret_key.lower():
        issues.append("CRITICAL: SECRET_KEY is set to insecure default string in production!")
    else:
        print("[OK] SECRET_KEY is custom configured.")

    # 2. CORS Check
    if is_prod and "*" in settings.cors_origins:
        issues.append("CRITICAL: CORS_ORIGINS includes wildcard '*' in production mode!")
    else:
        print(f"[OK] CORS allowlist configured ({len(settings.cors_origins)} origins).")

    # 3. Debug Check
    if is_prod and settings.debug:
        issues.append("CRITICAL: DEBUG is enabled in production!")
    else:
        print(f"[OK] Debug mode: {settings.debug}")

    # 4. Database Connection & PostGIS Verification
    if settings.app_env != "test":
        print("[..] Testing PostgreSQL and PostGIS connectivity...")
        db_service = DatabaseService(settings=settings)
        try:
            db_service.initialize()
            probe = db_service.probe
            if probe is not None:
                res = await probe.check()
                if res.ok:
                    pg_version = res.metadata.get("postgres_version", "unknown")
                    postgis_version = res.metadata.get("postgis_version", "unknown")
                    print(f"[OK] PostgreSQL: {pg_version}")
                    print(f"[OK] PostGIS Extension: {postgis_version}")
                else:
                    issues.append(f"Database readiness probe failed: {res.detail}")
            await db_service.dispose()
        except Exception as exc:
            issues.append(f"Database connection failed: {exc}")
    else:
        print("[SKIP] Database probe skipped for test profile.")

    print("=====================================================================")
    if not issues:
        print("RESULT: All production configuration checks PASSED.")
        print("=====================================================================")
        return True, []
    else:
        print(f"RESULT: Configuration checks FAILED with {len(issues)} issue(s):")
        for idx, err in enumerate(issues, 1):
            print(f"  [{idx}] {err}")
        print("=====================================================================")
        return False, issues


def main():
    parser = argparse.ArgumentParser(description="Verify WeatherGPT configuration.")
    parser.add_argument("--env-file", default=None, help="Path to environment file to test")
    args = parser.parse_args()

    if args.env_file:
        settings = Settings(_env_file=args.env_file)
    else:
        settings = Settings()

    success, _ = asyncio.run(verify_configuration(settings))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
