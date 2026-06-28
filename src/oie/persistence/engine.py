from __future__ import annotations

from sqlalchemy import Engine, create_engine

from oie.persistence.database import DatabaseSettings, resolve_database_settings


def create_database_engine(settings: DatabaseSettings) -> Engine:
    connect_args = {}

    if settings.backend == "sqlite":
        connect_args = {"check_same_thread": False}

    return create_engine(
        settings.url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_database_engine_from_config(config: dict | None = None) -> Engine:
    return create_database_engine(resolve_database_settings(config or {}))
