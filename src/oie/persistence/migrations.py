from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from oie.persistence.database import DatabaseSettings, resolve_database_settings


def build_alembic_config(settings: DatabaseSettings) -> Config:
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.url)
    return config


def run_database_migrations(
    config: dict | None = None,
    revision: str = "head",
) -> None:
    settings = resolve_database_settings(config or {})
    alembic_config = build_alembic_config(settings)
    command.upgrade(alembic_config, revision)
