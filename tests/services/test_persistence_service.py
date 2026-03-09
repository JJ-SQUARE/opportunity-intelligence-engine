from __future__ import annotations

import sqlite3

from oie.orchestration.run_context import RunContext
from oie.services.persistence_service import PersistenceService


def test_persistence_service_writes_full_run_snapshot_including_company_scores(tmp_path):
    db_path = tmp_path / "oie_test.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_collected_raw"] = 10
    ctx.metrics["companies_detected"] = 4
    ctx.add_provider_event(
        provider="openai",
        event_type="request_started",
        message="Starting operation=classify_company",
        metadata={"attempt": 1},
    )
    ctx.provider_state["company_merge_candidates"] = [
        {
            "company_key_left": "cmp_a",
            "company_key_right": "cmp_b",
            "reason": "same_domain",
            "confidence": 0.9,
        }
    ]

    companies = [
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
    ]

    jobs = [
        {
            "title": "Backend Engineer",
            "company": "Acme Inc.",
            "company_key": "cmp_a",
            "location": "Remote",
            "job_url": "https://acme.com/jobs/1",
            "apply_url": "https://acme.com/apply/1",
            "description": "Python role",
            "source": "google_jobs",
            "detected_at": "2026-03-09",
        }
    ]

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/janedoe",
        }
    ]

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="ok", companies=companies, jobs=jobs, leads=leads)

    conn = sqlite3.connect(db_path)
    try:
        run_row = conn.execute("SELECT run_id, status FROM runs").fetchone()
        company_score_rows = conn.execute(
            "SELECT company_key, opportunity_score, score_openings FROM company_scores"
        ).fetchall()
        job_rows = conn.execute(
            "SELECT company_key, title, company, job_url FROM jobs"
        ).fetchall()
        lead_rows = conn.execute(
            "SELECT company_key, contact_name, email FROM leads"
        ).fetchall()
    finally:
        conn.close()

    assert run_row is not None
    assert run_row[1] == "ok"
    assert company_score_rows[0][0] == "cmp_a"
    assert company_score_rows[0][1] == 42
    assert company_score_rows[0][2] == 16
    assert job_rows[0][0] == "cmp_a"
    assert lead_rows[0][0] == "cmp_a"
