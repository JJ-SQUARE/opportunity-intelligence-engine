from __future__ import annotations

from typing import Any, Dict

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
