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
