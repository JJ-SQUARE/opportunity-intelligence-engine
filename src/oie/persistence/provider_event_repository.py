from __future__ import annotations

import json
from typing import Any, Dict, List

from oie.persistence.models import ProviderEvent
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class ProviderEventRepository(RepositoryBase):
    def replace_events(self, run_id: str, provider_events: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute("DELETE FROM provider_events WHERE run_id = ?", (run_id,))
                conn.executemany(
                    """
                    INSERT INTO provider_events (run_id, provider, event_type, status_code, message, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            event.get("provider"),
                            event.get("event_type"),
                            event.get("status_code"),
                            event.get("message"),
                            json.dumps(event.get("metadata", {}), ensure_ascii=False),
                        )
                        for event in provider_events
                    ],
                )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(ProviderEvent).filter(ProviderEvent.run_id == run_id).delete()
            session.add_all(
                [
                    ProviderEvent(
                        run_id=run_id,
                        provider=str(event.get("provider") or ""),
                        event_type=str(event.get("event_type") or ""),
                        status_code=event.get("status_code"),
                        message=event.get("message"),
                        metadata_json=json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    )
                    for event in provider_events
                ]
            )
            session.commit()

    def list_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT run_id, provider, event_type, status_code, message, metadata_json, created_at
                    FROM provider_events
                    WHERE run_id = ?
                    ORDER BY id ASC
                    """,
                    (run_id,),
                ).fetchall()

                out: List[Dict[str, Any]] = []
                for row in rows:
                    record = dict(row)
                    metadata_json = record.get("metadata_json")
                    try:
                        record["metadata"] = json.loads(metadata_json) if metadata_json else {}
                    except Exception:
                        record["metadata"] = {}
                    out.append(record)
                return out
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(ProviderEvent)
                .filter(ProviderEvent.run_id == run_id)
                .order_by(ProviderEvent.id.asc())
                .all()
            )

            out: List[Dict[str, Any]] = []
            for row in rows:
                try:
                    metadata = json.loads(row.metadata_json) if row.metadata_json else {}
                except Exception:
                    metadata = {}
                out.append(
                    {
                        "run_id": row.run_id,
                        "provider": row.provider,
                        "event_type": row.event_type,
                        "status_code": row.status_code,
                        "message": row.message,
                        "metadata_json": row.metadata_json,
                        "created_at": row.created_at,
                        "metadata": metadata,
                    }
                )
            return out


