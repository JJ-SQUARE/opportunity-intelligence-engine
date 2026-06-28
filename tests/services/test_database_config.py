from __future__ import annotations

from oie.persistence.database import resolve_database_settings


def test_resolve_database_settings_defaults_to_sqlite_path():
    settings = resolve_database_settings({})

    assert settings.backend == "sqlite"
    assert settings.path == "data/oie.db"
    assert settings.url == "sqlite:///data/oie.db"


def test_resolve_database_settings_uses_configured_sqlite_path():
    settings = resolve_database_settings({"database": {"path": "tmp/test.db"}})

    assert settings.backend == "sqlite"
    assert settings.path == "tmp/test.db"
    assert settings.url == "sqlite:///tmp/test.db"


def test_resolve_database_settings_supports_explicit_postgres_url():
    settings = resolve_database_settings(
        {
            "database": {
                "backend": "postgresql",
                "url": "postgresql+psycopg://user:pass@localhost:5432/oie",
            }
        }
    )

    assert settings.backend == "postgresql"
    assert settings.path is None
    assert settings.url == "postgresql+psycopg://user:pass@localhost:5432/oie"


def test_resolve_database_settings_builds_postgres_url_from_parts():
    settings = resolve_database_settings(
        {
            "database": {
                "backend": "postgres",
                "host": "db",
                "port": 5433,
                "dbname": "oie_test",
                "user": "app",
                "password": "secret",
            }
        }
    )

    assert settings.backend == "postgresql"
    assert settings.path is None
    assert settings.url == "postgresql+psycopg://app:secret@db:5433/oie_test"

def test_run_context_exposes_database_settings_for_sqlite(tmp_path):
    from oie.orchestration.run_context import RunContext

    db_path = tmp_path / "oie.db"
    ctx = RunContext.create(
        config={
            "database": {"backend": "sqlite", "path": str(db_path)},
            "runs": {"path": str(tmp_path / "runs")},
        },
        flags={},
    )

    assert ctx.paths["database"].backend == "sqlite"
    assert ctx.paths["database"].path == str(db_path)
    assert ctx.paths["database"].url.startswith("sqlite:///")
    assert ctx.paths["db_path"] == str(db_path)


def test_run_context_exposes_database_settings_for_postgres(tmp_path):
    from oie.orchestration.run_context import RunContext

    ctx = RunContext.create(
        config={
            "database": {
                "backend": "postgresql",
                "url": "postgresql+psycopg://user:pass@localhost:5432/oie",
            },
            "runs": {"path": str(tmp_path / "runs")},
        },
        flags={},
    )

    assert ctx.paths["database"].backend == "postgresql"
    assert ctx.paths["database"].path is None
    assert ctx.paths["database"].url == "postgresql+psycopg://user:pass@localhost:5432/oie"
    assert ctx.paths["db_path"] == "data/oie.db"

def test_connection_factory_opens_sqlite_connection(tmp_path):
    from oie.persistence.connection_factory import ConnectionFactory
    from oie.persistence.database import resolve_database_settings

    db_path = tmp_path / "factory.db"
    settings = resolve_database_settings(
        {"database": {"backend": "sqlite", "path": str(db_path)}}
    )

    conn = ConnectionFactory(settings).connect()
    try:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO sample (name) VALUES (?)", ("Acme",))
        row = conn.execute("SELECT name FROM sample").fetchone()
        assert row["name"] == "Acme"
    finally:
        conn.close()


def test_connection_factory_blocks_postgres_until_repositories_are_migrated():
    from oie.persistence.connection_factory import (
        ConnectionFactory,
        UnsupportedDatabaseBackendError,
    )
    from oie.persistence.database import resolve_database_settings

    settings = resolve_database_settings(
        {
            "database": {
                "backend": "postgresql",
                "url": "postgresql+psycopg://user:pass@localhost:5432/oie",
            }
        }
    )

    try:
        ConnectionFactory(settings).connect()
    except UnsupportedDatabaseBackendError as exc:
        assert "SQLite-only" in str(exc)
        assert "PostgreSQL persistence" in str(exc)
    else:
        raise AssertionError("Expected UnsupportedDatabaseBackendError")

def test_persistence_context_from_sqlite_path_opens_connection(tmp_path):
    from oie.persistence.context import PersistenceContext

    db_path = tmp_path / "context.db"
    context = PersistenceContext.from_sqlite_path(str(db_path))

    assert context.backend == "sqlite"
    assert context.path == str(db_path)
    assert context.url.startswith("sqlite:///")

    conn = context.connection()
    try:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO sample (name) VALUES (?)", ("Acme",))
        row = conn.execute("SELECT name FROM sample").fetchone()
        assert row["name"] == "Acme"
    finally:
        conn.close()


def test_persistence_context_from_run_context_uses_database_settings(tmp_path):
    from oie.orchestration.run_context import RunContext
    from oie.persistence.context import PersistenceContext

    db_path = tmp_path / "run_context.db"
    ctx = RunContext.create(
        config={
            "database": {"backend": "sqlite", "path": str(db_path)},
            "runs": {"path": str(tmp_path / "runs")},
        },
        flags={},
    )

    context = PersistenceContext.from_run_context(ctx)

    assert context.backend == "sqlite"
    assert context.path == str(db_path)
    assert context.url.startswith("sqlite:///")


def test_persistence_context_from_run_context_supports_postgres_settings(tmp_path):
    from oie.orchestration.run_context import RunContext
    from oie.persistence.context import PersistenceContext

    ctx = RunContext.create(
        config={
            "database": {
                "backend": "postgresql",
                "url": "postgresql+psycopg://user:pass@localhost:5432/oie",
            },
            "runs": {"path": str(tmp_path / "runs")},
        },
        flags={},
    )

    context = PersistenceContext.from_run_context(ctx)

    assert context.backend == "postgresql"
    assert context.path is None
    assert context.url == "postgresql+psycopg://user:pass@localhost:5432/oie"

def test_repository_base_uses_persistence_context_connection(tmp_path):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.repositories import RunRepository
    from oie.persistence.sqlite import initialize_database

    db_path = tmp_path / "repo_base.db"
    initialize_database(str(db_path))

    persistence = PersistenceContext.from_sqlite_path(str(db_path))
    repository = RunRepository(persistence=persistence)

    repository.upsert_run(
        run_id="run_1",
        run_date="2026-01-01T00:00:00+00:00",
        status="completed",
        mode="default",
    )

    assert repository.get_run("run_1")["status"] == "completed"


def test_repository_base_preserves_db_path_compatibility(tmp_path):
    from oie.persistence.repositories import RunRepository
    from oie.persistence.sqlite import initialize_database

    db_path = tmp_path / "repo_compat.db"
    initialize_database(str(db_path))

    repository = RunRepository(db_path=str(db_path))
    repository.upsert_run(
        run_id="run_compat",
        run_date="2026-01-01T00:00:00+00:00",
        status="completed",
        mode="default",
    )

    assert repository.get_run("run_compat")["mode"] == "default"

def test_create_database_engine_for_sqlite(tmp_path):
    from sqlalchemy import text

    from oie.persistence.database import resolve_database_settings
    from oie.persistence.engine import create_database_engine

    db_path = tmp_path / "engine.db"
    settings = resolve_database_settings(
        {"database": {"backend": "sqlite", "path": str(db_path)}}
    )

    engine = create_database_engine(settings)

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)"))
        conn.execute(text("INSERT INTO sample (name) VALUES (:name)"), {"name": "Acme"})
        row = conn.execute(text("SELECT name FROM sample")).fetchone()

    assert row[0] == "Acme"


def test_database_settings_supports_postgres_url_without_driver_connection():
    from oie.persistence.database import resolve_database_settings

    settings = resolve_database_settings(
        {
            "database": {
                "backend": "postgresql",
                "url": "postgresql+psycopg://user:pass@localhost:5432/oie",
            }
        }
    )

    assert settings.backend == "postgresql"
    assert settings.url == "postgresql+psycopg://user:pass@localhost:5432/oie"
