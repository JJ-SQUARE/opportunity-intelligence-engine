from __future__ import annotations

import sqlite3
from typing import Any

from oie.orchestration.run_context import RunContext
from oie.persistence.connection_factory import ConnectionFactory
from oie.persistence.database import DatabaseSettings, resolve_database_settings


class PersistenceContext:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings
        self.connection_factory = ConnectionFactory(settings)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> "PersistenceContext":
        return cls(resolve_database_settings(config or {}))

    @classmethod
    def from_run_context(cls, ctx: RunContext) -> "PersistenceContext":
        settings = ctx.paths.get("database")
        if isinstance(settings, DatabaseSettings):
            return cls(settings)
        return cls(resolve_database_settings(ctx.config))

    @classmethod
    def from_sqlite_path(cls, db_path: str) -> "PersistenceContext":
        return cls(
            resolve_database_settings(
                {"database": {"backend": "sqlite", "path": db_path}}
            )
        )

    @property
    def backend(self) -> str:
        return self.settings.backend

    @property
    def path(self) -> str | None:
        return self.settings.path

    @property
    def url(self) -> str:
        return self.settings.url

    def connection(self) -> sqlite3.Connection:
        return self.connection_factory.connect()
