from __future__ import annotations

from typing import Any, Dict, Optional

from oie.persistence.models import Run
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class RunRepository(RepositoryBase):
    def upsert_run(self, run_id: str, run_date: str, status: str, mode: str) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
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
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            existing = session.get(Run, run_id)
            if existing is None:
                session.add(
                    Run(
                        run_id=run_id,
                        run_date=run_date,
                        status=status,
                        mode=mode,
                    )
                )
            else:
                existing.run_date = run_date
                existing.status = status
                existing.mode = mode
            session.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT run_id, run_date, status, mode, created_at
                    FROM runs
                    WHERE run_id = ?
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            run = session.get(Run, run_id)
            if run is None:
                return None
            return {
                "run_id": run.run_id,
                "run_date": run.run_date,
                "status": run.status,
                "mode": run.mode,
                "created_at": run.created_at,
            }


