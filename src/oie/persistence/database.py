from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


DEFAULT_SQLITE_PATH = "data/oie.db"
DEFAULT_BACKEND = "sqlite"


@dataclass(frozen=True)
class DatabaseSettings:
    backend: str
    url: str
    path: str | None = None


def _resolve_env_value(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "").strip()
    return raw


def resolve_database_settings(config: dict[str, Any] | None = None) -> DatabaseSettings:
    database_config = ((config or {}).get("database") or {})
    backend = str(database_config.get("backend") or DEFAULT_BACKEND).strip().lower()

    url = _resolve_env_value(database_config.get("url") or os.getenv("OIE_DATABASE_URL", ""))
    path = str(database_config.get("path") or DEFAULT_SQLITE_PATH).strip()

    if backend in {"postgres", "postgresql"}:
        if not url:
            host = _resolve_env_value(database_config.get("host") or os.getenv("OIE_POSTGRES_HOST", "localhost"))
            port = _resolve_env_value(database_config.get("port") or os.getenv("OIE_POSTGRES_PORT", "5432"))
            dbname = _resolve_env_value(database_config.get("dbname") or os.getenv("OIE_POSTGRES_DB", "oie"))
            user = _resolve_env_value(database_config.get("user") or os.getenv("OIE_POSTGRES_USER", "oie"))
            password = _resolve_env_value(database_config.get("password") or os.getenv("OIE_POSTGRES_PASSWORD", "oie"))
            url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        return DatabaseSettings(backend="postgresql", url=url, path=None)

    if backend != "sqlite":
        raise ValueError(f"Unsupported database backend: {backend}")

    if not url:
        url = f"sqlite:///{path}"

    return DatabaseSettings(backend="sqlite", url=url, path=path)


def create_database_engine(config: dict[str, Any] | None = None) -> Engine:
    settings = resolve_database_settings(config)

    connect_args: dict[str, Any] = {}
    if settings.backend == "sqlite":
        connect_args["check_same_thread"] = False

    return create_engine(settings.url, future=True, connect_args=connect_args)
