from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from oie.persistence.database import DatabaseSettings, resolve_database_settings


class UnsupportedDatabaseBackendError(RuntimeError):
    pass


def _sqlite_path_from_settings(settings: DatabaseSettings) -> str:
    path = settings.path or "data/oie.db"
    db_file = Path(path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return path


class ConnectionFactory:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> "ConnectionFactory":
        return cls(resolve_database_settings(config or {}))

    def connect(self) -> sqlite3.Connection:
        if self.settings.backend == "sqlite":
            conn = sqlite3.connect(_sqlite_path_from_settings(self.settings))
            conn.row_factory = sqlite3.Row
            return conn

        raise UnsupportedDatabaseBackendError(
            f"Database backend is configured as {self.settings.backend}, "
            "but repository connections are still SQLite-only. "
            "Migrate repositories before enabling PostgreSQL persistence."
        )


def get_connection_from_settings(settings: DatabaseSettings) -> sqlite3.Connection:
    return ConnectionFactory(settings).connect()
