from __future__ import annotations

import sqlite3

from oie.orchestration.run_context import RunContext
from oie.services.persistence_service import PersistenceService


def test_persistence_service_writes_run_metrics_provider_events_and_companies(tmp_path):
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
        }
    ]

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="ok", companies=companies)

    conn = sqlite3.connect(db_path)
    try:
        run_row = conn.execute("SELECT run_id, status FROM runs").fetchone()
        metric_rows = conn.execute(
            "SELECT metric_key, metric_value FROM run_metrics ORDER BY metric_key"
        ).fetchall()
        provider_event_rows = conn.execute(
            "SELECT provider, event_type, message FROM provider_events"
        ).fetchall()
        company_rows = conn.execute(
            "SELECT company_key, company_display, company_normalized, resolved_domain FROM companies"
        ).fetchall()
        alias_rows = conn.execute(
            "SELECT company_key, alias_value, alias_normalized FROM company_aliases"
        ).fetchall()
        domain_rows = conn.execute(
            "SELECT company_key, domain, source, confidence FROM domains"
        ).fetchall()
        merge_rows = conn.execute(
            "SELECT company_key_left, company_key_right, reason, confidence FROM company_merge_candidates"
        ).fetchall()
    finally:
        conn.close()

    assert run_row is not None
    assert run_row[1] == "ok"
    assert ("companies_detected", "4") in metric_rows
    assert ("jobs_collected_raw", "10") in metric_rows
    assert provider_event_rows[0][0] == "openai"
    assert provider_event_rows[0][1] == "request_started"
    assert company_rows[0][0] == "cmp_a"
    assert company_rows[0][1] == "Acme Inc."
    assert company_rows[0][2] == "acme"
    assert company_rows[0][3] == "acme.com"
    assert alias_rows[0][0] == "cmp_a"
    assert alias_rows[0][1] == "Acme Inc."
    assert alias_rows[0][2] == "acme"
    assert domain_rows[0][0] == "cmp_a"
    assert domain_rows[0][1] == "acme.com"
    assert merge_rows[0][0] == "cmp_a"
    assert merge_rows[0][1] == "cmp_b"
