from __future__ import annotations

import json
from typing import Any, Dict, List

from oie.persistence.sqlite import get_connection


class RunRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def upsert_run(self, run_id: str, run_date: str, status: str, mode: str) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO runs (run_id, run_date, status, mode)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    run_date = excluded.run_date,
                    status = excluded.status,
                    mode = excluded.mode
                """,
                (run_id, run_date, status, mode),
            )
            conn.commit()
        finally:
            conn.close()


class RunMetricsRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM run_metrics WHERE run_id = ?", (run_id,))
            conn.executemany(
                """
                INSERT INTO run_metrics (run_id, metric_key, metric_value)
                VALUES (?, ?, ?)
                """,
                [(run_id, key, str(value)) for key, value in metrics.items()],
            )
            conn.commit()
        finally:
            conn.close()


class ProviderEventRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_events(self, run_id: str, provider_events: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM provider_events WHERE run_id = ?", (run_id,))
            conn.executemany(
                """
                INSERT INTO provider_events (run_id, provider, event_type, message, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        event.get("provider"),
                        event.get("event_type"),
                        event.get("message"),
                        json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    )
                    for event in provider_events
                ],
            )
            conn.commit()
        finally:
            conn.close()
