from __future__ import annotations

from typing import Any, Dict, List

from oie.persistence.models import ProviderOperationMetric
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class ProviderOperationMetricsRepository(RepositoryBase):
    def replace_rows(self, run_id: str, rows: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute("DELETE FROM provider_operation_metrics WHERE run_id = ?", (run_id,))
                if rows:
                    conn.executemany(
                        """
                        INSERT INTO provider_operation_metrics (
                            run_id,
                            provider,
                            operation,
                            max_calls,
                            used_calls,
                            remaining_calls,
                            started,
                            success,
                            retry_count,
                            blocked_budget,
                            blocked_provider,
                            errors_timeout,
                            errors_rate_limit,
                            errors_http_5xx,
                            errors_execution_error,
                            errors_auth,
                            errors_permission
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                run_id,
                                row.get("provider"),
                                row.get("operation"),
                                row.get("max_calls"),
                                row.get("used_calls", 0),
                                row.get("remaining_calls"),
                                row.get("started", 0),
                                row.get("success", 0),
                                row.get("retry_count", 0),
                                row.get("blocked_budget", 0),
                                row.get("blocked_provider", 0),
                                row.get("errors_timeout", 0),
                                row.get("errors_rate_limit", 0),
                                row.get("errors_http_5xx", 0),
                                row.get("errors_execution_error", 0),
                                row.get("errors_auth", 0),
                                row.get("errors_permission", 0),
                            )
                            for row in rows
                        ],
                    )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(ProviderOperationMetric).filter(
                ProviderOperationMetric.run_id == run_id
            ).delete()
            session.add_all(
                [
                    ProviderOperationMetric(
                        run_id=run_id,
                        provider=str(row.get("provider") or ""),
                        operation=str(row.get("operation") or ""),
                        max_calls=row.get("max_calls"),
                        used_calls=int(row.get("used_calls", 0) or 0),
                        remaining_calls=row.get("remaining_calls"),
                        started=int(row.get("started", 0) or 0),
                        success=int(row.get("success", 0) or 0),
                        retry_count=int(row.get("retry_count", 0) or 0),
                        blocked_budget=int(row.get("blocked_budget", 0) or 0),
                        blocked_provider=int(row.get("blocked_provider", 0) or 0),
                        errors_timeout=int(row.get("errors_timeout", 0) or 0),
                        errors_rate_limit=int(row.get("errors_rate_limit", 0) or 0),
                        errors_http_5xx=int(row.get("errors_http_5xx", 0) or 0),
                        errors_execution_error=int(row.get("errors_execution_error", 0) or 0),
                        errors_auth=int(row.get("errors_auth", 0) or 0),
                        errors_permission=int(row.get("errors_permission", 0) or 0),
                    )
                    for row in rows
                ]
            )
            session.commit()

