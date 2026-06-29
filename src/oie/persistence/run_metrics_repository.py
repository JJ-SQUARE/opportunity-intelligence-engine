from __future__ import annotations

from typing import Any, Dict

from oie.persistence.models import RunMetric
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class RunMetricsRepository(RepositoryBase):
    def replace_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
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
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(RunMetric).filter(RunMetric.run_id == run_id).delete()
            session.add_all(
                [
                    RunMetric(
                        run_id=run_id,
                        metric_key=str(key),
                        metric_value=str(value),
                    )
                    for key, value in metrics.items()
                ]
            )
            session.commit()

    def get_metrics(self, run_id: str) -> Dict[str, Any]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT metric_key, metric_value
                    FROM run_metrics
                    WHERE run_id = ?
                    ORDER BY metric_key ASC
                    """,
                    (run_id,),
                ).fetchall()
                return {row["metric_key"]: row["metric_value"] for row in rows}
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(RunMetric)
                .filter(RunMetric.run_id == run_id)
                .order_by(RunMetric.metric_key.asc())
                .all()
            )
            return {row.metric_key: row.metric_value for row in rows}


