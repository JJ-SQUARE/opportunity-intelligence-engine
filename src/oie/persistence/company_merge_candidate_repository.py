from __future__ import annotations
from typing import Any, Dict, List
from oie.persistence.models import CompanyMergeCandidate
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory
class CompanyMergeCandidateRepository(RepositoryBase):
    def replace_merge_candidates(self, run_id: str, candidates: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._replace_merge_candidates_orm(run_id, candidates)
            return

        conn = self.connection()
        try:
            conn.execute("DELETE FROM company_merge_candidates WHERE run_id = ?", (run_id,))
            if candidates:
                conn.executemany(
                    """
                    INSERT INTO company_merge_candidates (
                        run_id,
                        company_key_left,
                        company_key_right,
                        reason,
                        confidence
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            candidate.get("company_key_left"),
                            candidate.get("company_key_right"),
                            candidate.get("reason"),
                            candidate.get("confidence"),
                        )
                        for candidate in candidates
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def _replace_merge_candidates_orm(self, run_id: str, candidates: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(CompanyMergeCandidate).filter(
                CompanyMergeCandidate.run_id == run_id
            ).delete()
            session.add_all(
                [
                    CompanyMergeCandidate(
                        run_id=run_id,
                        company_key_left=str(candidate.get("company_key_left") or ""),
                        company_key_right=str(candidate.get("company_key_right") or ""),
                        reason=str(candidate.get("reason") or ""),
                        confidence=float(candidate.get("confidence", 0.0) or 0.0),
                    )
                    for candidate in candidates
                ]
            )
            session.commit()

