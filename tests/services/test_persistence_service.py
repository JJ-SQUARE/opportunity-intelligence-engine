from __future__ import annotations

import sqlite3

from oie.orchestration.run_context import RunContext
from oie.services.persistence_service import PersistenceService


def test_persistence_service_writes_run_and_metrics(tmp_path):
    db_path = tmp_path / "oie_test.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_collected_raw"] = 10
    ctx.metrics["companies_detected"] = 4

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="ok")

    conn = sqlite3.connect(db_path)
    try:
        run_row = conn.execute("SELECT run_id, status FROM runs").fetchone()
        metric_rows = conn.execute(
            "SELECT metric_key, metric_value FROM run_metrics ORDER BY metric_key"
        ).fetchall()
    finally:
        conn.close()

    assert run_row is not None
    assert run_row[1] == "ok"
    assert ("companies_detected", "4") in metric_rows
    assert ("jobs_collected_raw", "10") in metric_rows
