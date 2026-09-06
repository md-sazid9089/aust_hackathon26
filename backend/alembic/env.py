"""Alembic environment: async engine, URL from app settings (DATABASE_URL), models as target metadata."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata


def _render_as_batch(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"}, render_as_batch=_render_as_batch(url or ""),
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # noqa: ANN001
    context.configure(
        connection=connection, target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite", compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    kwargs: dict = {"prefix": "sqlalchemy.", "poolclass": pool.NullPool}
    if "+asyncpg" in url:
        # Same workaround as app/db/session.py for the Supabase transaction pooler (6543).
        kwargs["connect_args"] = {"statement_cache_size": 0}
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), **kwargs)
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
