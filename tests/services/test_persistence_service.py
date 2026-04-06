from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.persistence.sqlite import get_connection
from oie.services.persistence_service import PersistenceService


def test_persistence_service_persist_run_snapshot_writes_core_records(tmp_path):
    db_path = tmp_path / "oie_test.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_after_dedupe"] = 2
    ctx.add_provider_event(
        provider="openai",
        event_type="execution_error",
        message="boom",
        metadata={"status_code": 500},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.9,
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
                "opportunity_score": 42,
                "score_openings": 16,
                "score_remote": 8,
                "score_contractor": 6,
                "score_multi_source": 10,
                "score_company_type": 2,
            }
        ],
        jobs=[
            {
                "title": "Backend Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-10",
            }
        ],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
            }
        ],
    )

    assert Path(db_path).exists()

    conn = get_connection(str(db_path))
    try:
        run_row = conn.execute(
            "SELECT run_id, status FROM runs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchone()
        assert run_row is not None
        assert run_row["status"] == "ok"

        metric_row = conn.execute(
            "SELECT metric_value FROM run_metrics WHERE run_id = ? AND metric_key = ?",
            (ctx.run_id, "jobs_after_dedupe"),
        ).fetchone()
        assert metric_row is not None
        assert metric_row["metric_value"] == "2"

        events = conn.execute(
            "SELECT provider, event_type, status_code FROM provider_events WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(events) == 1
        assert events[0]["provider"] == "openai"

        companies = conn.execute(
            "SELECT company_key FROM companies"
        ).fetchall()
        assert len(companies) == 1
        assert companies[0]["company_key"] == "cmp_a"

        jobs = conn.execute(
            "SELECT company_key FROM jobs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(jobs) == 1
        assert jobs[0]["company_key"] == "cmp_a"

        leads = conn.execute(
            "SELECT email FROM leads WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(leads) == 1
        assert leads[0]["email"] == "jane@acme.com"
    finally:
        conn.close()


def test_persistence_service_persist_run_snapshot_allows_optional_entities(tmp_path):
    db_path = tmp_path / "oie_test_optional.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="partial")

    conn = get_connection(str(db_path))
    try:
        run_row = conn.execute(
            "SELECT run_id, status FROM runs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchone()

        assert run_row is not None
        assert run_row["status"] == "partial"
    finally:
        conn.close()
