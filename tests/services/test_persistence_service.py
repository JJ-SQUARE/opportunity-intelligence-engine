from __future__ import annotations

import sqlite3

from oie.orchestration.run_context import RunContext
from oie.services.persistence_service import PersistenceService


def test_persistence_service_writes_run_metrics_and_provider_events(tmp_path):
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

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="ok")

    conn = sqlite3.connect(db_path)
    try:
        run_row = conn.execute("SELECT run_id, status FROM runs").fetchone()
        metric_rows = conn.execute(
            "SELECT metric_key, metric_value FROM run_metrics ORDER BY metric_key"
        ).fetchall()
        provider_event_rows = conn.execute(
            "SELECT provider, event_type, message FROM provider_events"
        ).fetchall()
    finally:
        conn.close()

    assert run_row is not None
    assert run_row[1] == "ok"
    assert ("companies_detected", "4") in metric_rows
    assert ("jobs_collected_raw", "10") in metric_rows
    assert provider_event_rows[0][0] == "openai"
    assert provider_event_rows[0][1] == "request_started"
