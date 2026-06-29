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

def test_create_session_factory_for_sqlite(tmp_path):
    from sqlalchemy import text

    from oie.persistence.database import resolve_database_settings
    from oie.persistence.session import create_session_factory

    db_path = tmp_path / "session.db"
    settings = resolve_database_settings(
        {"database": {"backend": "sqlite", "path": str(db_path)}}
    )

    SessionFactory = create_session_factory(settings)

    with SessionFactory() as session:
        session.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)"))
        session.execute(text("INSERT INTO sample (name) VALUES (:name)"), {"name": "Acme"})
        session.commit()

    with SessionFactory() as session:
        row = session.execute(text("SELECT name FROM sample")).fetchone()

    assert row[0] == "Acme"


def test_create_session_factory_from_config_for_sqlite(tmp_path):
    from sqlalchemy import text

    from oie.persistence.session import create_session_factory_from_config

    db_path = tmp_path / "session_from_config.db"
    SessionFactory = create_session_factory_from_config(
        {"database": {"backend": "sqlite", "path": str(db_path)}}
    )

    with SessionFactory() as session:
        session.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)"))
        session.execute(text("INSERT INTO sample (name) VALUES (:name)"), {"name": "Acme"})
        session.commit()

    with SessionFactory() as session:
        row = session.execute(text("SELECT name FROM sample")).fetchone()

    assert row[0] == "Acme"

def test_run_orm_model_can_create_and_query_sqlite(tmp_path):
    from oie.persistence.database import resolve_database_settings
    from oie.persistence.models import Base, Run
    from oie.persistence.session import create_session_factory

    db_path = tmp_path / "orm_run.db"
    settings = resolve_database_settings(
        {"database": {"backend": "sqlite", "path": str(db_path)}}
    )
    SessionFactory = create_session_factory(settings)

    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_orm_1",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.commit()

    with SessionFactory() as session:
        run = session.get(Run, "run_orm_1")

    assert run is not None
    assert run.status == "completed"
    assert run.mode == "default"

def test_run_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base
    from oie.persistence.repositories import RunRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    repository = RunRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.upsert_run(
        run_id="run_orm_repo",
        run_date="2026-01-01T00:00:00+00:00",
        status="completed",
        mode="default",
    )

    saved = repository.get_run("run_orm_repo")

    assert saved is not None
    assert saved["run_id"] == "run_orm_repo"
    assert saved["status"] == "completed"

    repository.upsert_run(
        run_id="run_orm_repo",
        run_date="2026-01-02T00:00:00+00:00",
        status="partial_success",
        mode="dry-run",
    )

    updated = repository.get_run("run_orm_repo")

    assert updated["status"] == "partial_success"
    assert updated["mode"] == "dry-run"

def test_run_metrics_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Run
    from oie.persistence.repositories import RunMetricsRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_metrics_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_metrics_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.commit()

    repository = RunMetricsRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_metrics(
        "run_metrics_orm",
        {
            "input_count": 10,
            "status": "completed",
        },
    )

    assert repository.get_metrics("run_metrics_orm") == {
        "input_count": "10",
        "status": "completed",
    }

    repository.replace_metrics(
        "run_metrics_orm",
        {
            "output_count": 7,
        },
    )

    assert repository.get_metrics("run_metrics_orm") == {
        "output_count": "7",
    }

def test_provider_event_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Run
    from oie.persistence.repositories import ProviderEventRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_provider_events_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_events_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.commit()

    repository = ProviderEventRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_events(
        "run_events_orm",
        [
            {
                "provider": "openai",
                "event_type": "request_started",
                "status_code": None,
                "message": "Started",
                "metadata": {"operation": "score"},
            },
            {
                "provider": "openai",
                "event_type": "request_succeeded",
                "status_code": 200,
                "message": "Done",
                "metadata": {"tokens": 123},
            },
        ],
    )

    events = repository.list_by_run("run_events_orm")

    assert [event["event_type"] for event in events] == [
        "request_started",
        "request_succeeded",
    ]
    assert events[0]["metadata"] == {"operation": "score"}
    assert events[1]["status_code"] == 200
    assert events[1]["metadata"] == {"tokens": 123}

    repository.replace_events(
        "run_events_orm",
        [
            {
                "provider": "hunter",
                "event_type": "blocked",
                "status_code": 403,
                "message": "Blocked",
                "metadata": {},
            }
        ],
    )

    replaced = repository.list_by_run("run_events_orm")

    assert len(replaced) == 1
    assert replaced[0]["provider"] == "hunter"
    assert replaced[0]["event_type"] == "blocked"

def test_provider_operation_metrics_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from sqlalchemy import select

    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, ProviderOperationMetric, Run
    from oie.persistence.repositories import ProviderOperationMetricsRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_provider_operation_metrics_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_provider_ops_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.commit()

    repository = ProviderOperationMetricsRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_rows(
        "run_provider_ops_orm",
        [
            {
                "provider": "openai",
                "operation": "score_lead",
                "max_calls": 10,
                "used_calls": 2,
                "remaining_calls": 8,
                "started": 2,
                "success": 1,
                "retry_count": 1,
                "blocked_budget": 0,
                "blocked_provider": 0,
                "errors_timeout": 1,
                "errors_rate_limit": 0,
                "errors_http_5xx": 0,
                "errors_execution_error": 0,
                "errors_auth": 0,
                "errors_permission": 0,
            }
        ],
    )

    with SessionFactory() as session:
        rows = session.execute(
            select(ProviderOperationMetric).where(
                ProviderOperationMetric.run_id == "run_provider_ops_orm"
            )
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].provider == "openai"
    assert rows[0].operation == "score_lead"
    assert rows[0].used_calls == 2
    assert rows[0].errors_timeout == 1

    repository.replace_rows(
        "run_provider_ops_orm",
        [
            {
                "provider": "hunter",
                "operation": "domain_search",
                "used_calls": 3,
            }
        ],
    )

    with SessionFactory() as session:
        replaced = session.execute(
            select(ProviderOperationMetric).where(
                ProviderOperationMetric.run_id == "run_provider_ops_orm"
            )
        ).scalars().all()

    assert len(replaced) == 1
    assert replaced[0].provider == "hunter"
    assert replaced[0].operation == "domain_search"
    assert replaced[0].used_calls == 3

def test_company_repository_read_methods_use_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Company
    from oie.persistence.repositories import CompanyRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_company_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add_all(
            [
                Company(
                    company_key="cmp_beta",
                    company_display="Beta",
                    company_normalized="beta",
                    company_root="beta",
                    resolved_domain="beta.com",
                    industry="Technology",
                ),
                Company(
                    company_key="cmp_acme",
                    company_display="Acme",
                    company_normalized="acme",
                    company_root="acme",
                    resolved_domain="acme.com",
                    industry="Finance",
                ),
            ]
        )
        session.commit()

    repository = CompanyRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    by_domain = repository.find_by_domain("acme.com")
    by_normalized = repository.find_by_normalized_and_domain("acme", "acme.com")
    companies = repository.list_companies()

    assert by_domain == {
        "company_key": "cmp_acme",
        "company_display": "Acme",
        "company_normalized": "acme",
        "company_root": "acme",
        "resolved_domain": "acme.com",
    }
    assert by_normalized == by_domain
    assert [company["company_display"] for company in companies] == ["Acme", "Beta"]
    assert companies[0]["industry"] == "Finance"

def test_company_repository_upsert_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base
    from oie.persistence.repositories import CompanyRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_company_upsert_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    repository = CompanyRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.upsert_companies(
        [
            {
                "company_key": "cmp_acme",
                "company_display": "Acme",
                "company_normalized": "acme",
                "company_root": "acme",
                "resolved_domain": "acme.com",
                "domain_source": "serpapi",
                "domain_confidence": 0.9,
                "domain_review_required": True,
                "company_identity_ai_valid": True,
                "industry": "Finance",
                "employee_range": "1001-5000",
                "linkedin_company_url": "https://linkedin.com/company/acme",
                "company_description": "Initial description",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.8,
            }
        ]
    )

    saved = repository.find_by_domain("acme.com")
    companies = repository.list_companies()

    assert saved["company_key"] == "cmp_acme"
    assert companies[0]["industry"] == "Finance"
    assert companies[0]["domain_review_required"] == 1

    repository.upsert_companies(
        [
            {
                "company_key": "cmp_acme",
                "company_display": "Acme Corp",
                "company_normalized": "acme",
                "company_root": None,
                "resolved_domain": "acme.com",
                "domain_source": "manual",
                "domain_confidence": 1.0,
                "company_identity_ai_valid": True,
                "industry": None,
                "employee_range": None,
                "company_description": None,
                "company_type_ai": None,
            }
        ]
    )

    updated = repository.list_companies()[0]

    assert updated["company_display"] == "Acme Corp"
    assert updated["company_root"] == "acme"
    assert updated["domain_source"] == "manual"
    assert updated["domain_confidence"] == 1.0
    assert updated["industry"] == "Finance"
    assert updated["employee_range"] == "1001-5000"
    assert updated["company_description"] == "Initial description"
    assert updated["company_type_ai"] == "end_client"

def test_alias_and_domain_repositories_use_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from sqlalchemy import select

    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Company, Domain
    from oie.persistence.repositories import CompanyAliasRepository, DomainRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_alias_domain_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Company(
                company_key="cmp_acme",
                company_display="Acme",
                company_normalized="acme",
                company_root="acme",
                resolved_domain="acme.com",
            )
        )
        session.commit()

    persistence = PersistenceContext(settings=postgres_like_settings)
    alias_repository = CompanyAliasRepository(persistence=persistence)
    domain_repository = DomainRepository(persistence=persistence)

    companies = [
        {
            "company_key": "cmp_acme",
            "company_normalized": "acme",
            "resolved_domain": "acme.com",
            "domain_source": "manual",
            "domain_confidence": 0.95,
            "aliases": ["ACME Inc", "Acme Corp"],
            "alias_type_map": {
                "ACME Inc": "acme inc",
                "ACME Inc__type": "legal_name",
                "Acme Corp": "acme corp",
                "Acme Corp__type": "observed_name",
            },
        }
    ]

    alias_repository.replace_aliases(companies)
    domain_repository.replace_domains(companies)

    found = alias_repository.find_company_by_alias_normalized("acme inc")

    assert found == {
        "company_key": "cmp_acme",
        "company_display": "Acme",
        "company_normalized": "acme",
        "resolved_domain": "acme.com",
    }

    with SessionFactory() as session:
        domains = session.execute(
            select(Domain).where(Domain.company_key == "cmp_acme")
        ).scalars().all()

    assert len(domains) == 1
    assert domains[0].domain == "acme.com"
    assert domains[0].source == "manual"
    assert domains[0].confidence == 0.95
    assert domains[0].is_primary == 1

    alias_repository.replace_aliases(
        [
            {
                "company_key": "cmp_acme",
                "company_normalized": "acme",
                "aliases": ["Acme Updated"],
                "alias_type_map": {
                    "Acme Updated": "acme updated",
                },
            }
        ]
    )
    domain_repository.replace_domains(
        [
            {
                "company_key": "cmp_acme",
                "resolved_domain": "updated-acme.com",
                "domain_source": "hunter",
                "domain_confidence": 0.8,
            }
        ]
    )

    assert alias_repository.find_company_by_alias_normalized("acme inc") is None
    assert alias_repository.find_company_by_alias_normalized("acme updated")["company_key"] == "cmp_acme"

    with SessionFactory() as session:
        replaced_domains = session.execute(
            select(Domain).where(Domain.company_key == "cmp_acme")
        ).scalars().all()

    assert len(replaced_domains) == 1
    assert replaced_domains[0].domain == "updated-acme.com"
    assert replaced_domains[0].source == "hunter"

def test_company_merge_candidate_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from sqlalchemy import select

    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, CompanyMergeCandidate, Run
    from oie.persistence.repositories import CompanyMergeCandidateRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_merge_candidates_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_merge_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.commit()

    repository = CompanyMergeCandidateRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_merge_candidates(
        "run_merge_orm",
        [
            {
                "company_key_left": "cmp_a",
                "company_key_right": "cmp_b",
                "reason": "same domain root",
                "confidence": 0.87,
            },
            {
                "company_key_left": "cmp_c",
                "company_key_right": "cmp_d",
                "reason": "same alias",
                "confidence": 0.65,
            },
        ],
    )

    with SessionFactory() as session:
        rows = session.execute(
            select(CompanyMergeCandidate).where(
                CompanyMergeCandidate.run_id == "run_merge_orm"
            )
        ).scalars().all()

    assert len(rows) == 2
    assert rows[0].company_key_left == "cmp_a"
    assert rows[0].company_key_right == "cmp_b"
    assert rows[0].reason == "same domain root"
    assert rows[0].confidence == 0.87

    repository.replace_merge_candidates(
        "run_merge_orm",
        [
            {
                "company_key_left": "cmp_x",
                "company_key_right": "cmp_y",
                "reason": "replacement",
            }
        ],
    )

    with SessionFactory() as session:
        replaced = session.execute(
            select(CompanyMergeCandidate).where(
                CompanyMergeCandidate.run_id == "run_merge_orm"
            )
        ).scalars().all()

    assert len(replaced) == 1
    assert replaced[0].company_key_left == "cmp_x"
    assert replaced[0].company_key_right == "cmp_y"
    assert replaced[0].reason == "replacement"
    assert replaced[0].confidence == 0.0

def test_job_repository_replace_jobs_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from sqlalchemy import select

    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Company, Job, Run
    from oie.persistence.repositories import JobRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_jobs_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_jobs_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.add(
            Company(
                company_key="cmp_acme",
                company_display="Acme",
                company_normalized="acme",
            )
        )
        session.commit()

    repository = JobRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_jobs(
        "run_jobs_orm",
        "2026-01-01T00:00:00+00:00",
        [
            {
                "title": "Senior Python Engineer",
                "company": "Acme",
                "company_key": "cmp_acme",
                "location": "Remote LATAM",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Build platforms",
                "source": "serpapi",
                "detected_at": "2026-01-01",
                "is_remote": True,
                "is_contractor": True,
                "is_full_time": False,
                "nearshore_friendly": True,
                "us_only": False,
                "remote_flag": True,
                "contractor_flag": True,
                "many_openings_signal": True,
                "offshore_mentioned": False,
                "urgency_hits": 2,
            }
        ],
    )

    with SessionFactory() as session:
        rows = session.execute(
            select(Job).where(Job.run_id == "run_jobs_orm")
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].title == "Senior Python Engineer"
    assert rows[0].company_key == "cmp_acme"
    assert rows[0].is_remote == 1
    assert rows[0].is_contractor == 1
    assert rows[0].is_full_time == 0
    assert rows[0].urgency_hits == 2
    assert rows[0].job_key.startswith("job_")
    assert rows[0].job_fingerprint.startswith("jobfp_")

    repository.replace_jobs(
        "run_jobs_orm",
        "2026-01-01T00:00:00+00:00",
        [
            {
                "title": "Data Engineer",
                "company": "Acme",
                "company_key": "cmp_acme",
                "location": "Mexico",
                "description": "Data pipelines",
            }
        ],
    )

    with SessionFactory() as session:
        replaced = session.execute(
            select(Job).where(Job.run_id == "run_jobs_orm")
        ).scalars().all()

    assert len(replaced) == 1
    assert replaced[0].title == "Data Engineer"
    assert replaced[0].is_remote == 0

def test_lead_repository_replace_and_list_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Company, Run
    from oie.persistence.repositories import LeadRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_leads_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_leads_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.add(
            Company(
                company_key="cmp_acme",
                company_display="Acme",
                company_normalized="acme",
            )
        )
        session.commit()

    repository = LeadRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_leads(
        "run_leads_orm",
        "2026-01-01T00:00:00+00:00",
        [
            {
                "company_key": "cmp_acme",
                "contact_name": " Jane Doe ",
                "contact_title": "VP Engineering",
                "email": " Jane@Example.COM ",
                "linkedin_url": "https://linkedin.com/in/jane",
                "lead_source": "apollo",
                "lead_confidence": 0.9,
                "email_quality_score": 85,
                "lead_capture_reason": "senior engineering buyer",
                "lead_relevance_score": 91,
                "lead_priority_label": "high",
                "lead_decision_maker_score": 0.8,
                "lead_icp_fit_score": 0.7,
                "lead_contact_completeness_score": 0.95,
                "lead_penalty_negative_title": 0,
                "lead_score_reason": "strong match",
                "lead_scoring_provider": "openai",
                "lead_scoring_model": "test-model",
                "lead_scoring_mode": "mock",
                "target_persona": "Engineering",
                "recommended_channel": "email",
            }
        ],
    )

    rows = repository.list_leads_by_run("run_leads_orm")

    assert len(rows) == 1
    assert rows[0]["company_key"] == "cmp_acme"
    assert rows[0]["contact_name"] == "Jane Doe"
    assert rows[0]["email"] == "jane@example.com"
    assert rows[0]["lead_confidence"] == 0.9
    assert rows[0]["email_quality_score"] == 85
    assert rows[0]["lead_key"].startswith("lead_")
    assert rows[0]["lead_fingerprint"].startswith("leadfp_")

    repository.replace_leads(
        "run_leads_orm",
        "2026-01-01T00:00:00+00:00",
        [
            {
                "company_key": "cmp_acme",
                "contact_name": "John Smith",
                "contact_title": "CTO",
                "linkedin_url": "https://linkedin.com/in/john",
            }
        ],
    )

    replaced = repository.list_leads_by_run("run_leads_orm")

    assert len(replaced) == 1
    assert replaced[0]["contact_name"] == "John Smith"
    assert replaced[0]["email"] == ""
    assert replaced[0]["lead_confidence"] == 0.0

def test_company_score_repository_uses_orm_for_non_sqlite_backend(tmp_path, monkeypatch):
    from sqlalchemy import select

    from oie.persistence.context import PersistenceContext
    from oie.persistence.database import DatabaseSettings
    from oie.persistence.models import Base, Company, CompanyScore, Run
    from oie.persistence.repositories import CompanyScoreRepository
    from oie.persistence.session import create_session_factory

    sqlite_db = tmp_path / "orm_company_scores_backend_simulation.db"
    sqlite_settings = DatabaseSettings(
        backend="sqlite",
        path=str(sqlite_db),
        url=f"sqlite:///{sqlite_db}",
    )
    postgres_like_settings = DatabaseSettings(
        backend="postgresql",
        path=None,
        url="postgresql+psycopg://user:pass@localhost:5432/oie",
    )

    def fake_create_session_factory(settings):
        assert settings.backend == "postgresql"
        return create_session_factory(sqlite_settings)

    monkeypatch.setattr(
        "oie.persistence.repositories.create_session_factory",
        fake_create_session_factory,
    )

    SessionFactory = create_session_factory(sqlite_settings)
    Base.metadata.create_all(bind=SessionFactory.kw["bind"])

    with SessionFactory() as session:
        session.add(
            Run(
                run_id="run_scores_orm",
                run_date="2026-01-01T00:00:00+00:00",
                status="completed",
                mode="default",
            )
        )
        session.add(
            Company(
                company_key="cmp_acme",
                company_display="Acme",
                company_normalized="acme",
            )
        )
        session.commit()

    repository = CompanyScoreRepository(
        persistence=PersistenceContext(settings=postgres_like_settings)
    )

    repository.replace_company_scores(
        "run_scores_orm",
        [
            {
                "company_key": "cmp_acme",
                "opportunity_score": 87,
                "opportunity_label": "high",
                "icp_bucket": "strong_fit",
                "commercial_bucket": "priority",
                "pain_urgency": "high",
                "recommended_service": "ASD",
                "reason": "many relevant openings",
                "score_openings": 10,
                "score_remote": 8,
                "score_icp_fit": 9,
                "primary_service_fit": "ASD",
                "buyer_persona_fit": "Engineering",
                "opportunity_score_reason": "strong demand",
                "scoring_provider": "openai",
                "scoring_model": "test-model",
                "scoring_mode": "mock",
            },
            {
                "company_key": None,
                "opportunity_score": 1,
            },
        ],
    )

    with SessionFactory() as session:
        rows = session.execute(
            select(CompanyScore).where(CompanyScore.run_id == "run_scores_orm")
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].company_key == "cmp_acme"
    assert rows[0].opportunity_score == 87
    assert rows[0].opportunity_label == "high"
    assert rows[0].recommended_service == "ASD"
    assert rows[0].score_openings == 10
    assert rows[0].scoring_provider == "openai"

    repository.replace_company_scores(
        "run_scores_orm",
        [
            {
                "company_key": "cmp_acme",
                "opportunity_score": 55,
                "opportunity_label": "medium",
            }
        ],
    )

    with SessionFactory() as session:
        replaced = session.execute(
            select(CompanyScore).where(CompanyScore.run_id == "run_scores_orm")
        ).scalars().all()

    assert len(replaced) == 1
    assert replaced[0].opportunity_score == 55
    assert replaced[0].opportunity_label == "medium"
