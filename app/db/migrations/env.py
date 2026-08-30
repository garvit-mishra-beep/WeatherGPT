"""Alembic migration environment (async, environment-driven).

Runs migrations against PostgreSQL + PostGIS using the application's async
(``asyncpg``) engine. The database URL comes from ``app.config.Settings``
(which itself reads ``.env``/environment), so there is a single source of truth
and no duplicated connection string in ``alembic.ini``.
"""

import asyncio
import logging
from logging.config import fileConfig
from pathlib import Path
import sys

# Ensure repository root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db.base import Base

# Import models package so their metadata is registered for autogenerate.
from app.db import models  # noqa: F401

config = context.config

# Wire the application's asyncpg URL (with proper driver scheme) into Alembic
# instead of any placeholder value present in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.async_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Direct the alembic logger to our structured logging setup.
logging.getLogger("alembic").setLevel(logging.INFO)

# Autogenerate target metadata from the shared declarative Base.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, do not connect)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations online using an async engine over asyncpg."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (execute against the live database)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
