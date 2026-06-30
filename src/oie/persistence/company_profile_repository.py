from __future__ import annotations

import json
from typing import Any, Dict, List

from oie.persistence.models import CompanyProfile
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class CompanyProfileRepository(RepositoryBase):
    def replace_company_profiles(self, run_id: str, profiles: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(CompanyProfile).filter(CompanyProfile.run_id == run_id).delete()

            for profile in profiles:
                session.add(
                    CompanyProfile(
                        company_key=str(profile.get("company_key") or "").strip(),
                        profile_id=str(profile.get("profile_id") or "").strip(),
                        service_line=profile.get("service_line"),
                        profile_name=profile.get("profile_name") or profile.get("name"),
                        run_id=run_id,
                        fit_score=profile.get("fit_score"),
                        decision=profile.get("decision"),
                        confidence=profile.get("confidence"),
                        reason=profile.get("reason"),
                        evidence_json=json.dumps(profile.get("evidence", [])),
                    )
                )

            session.commit()
