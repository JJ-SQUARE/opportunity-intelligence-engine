from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from oie.persistence.database import DatabaseSettings, resolve_database_settings
from oie.persistence.engine import create_database_engine


def create_session_factory(settings: DatabaseSettings) -> sessionmaker[Session]:
    engine = create_database_engine(settings)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def create_session_factory_from_config(config: dict | None = None) -> sessionmaker[Session]:
    return create_session_factory(resolve_database_settings(config or {}))
