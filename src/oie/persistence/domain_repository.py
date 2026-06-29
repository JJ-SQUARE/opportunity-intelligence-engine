from __future__ import annotations

from typing import Any, Dict, List

from oie.persistence.models import Domain
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class DomainRepository(RepositoryBase):
    def replace_domains(self, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
                if company_keys:
                    placeholders = ",".join("?" for _ in company_keys)
                    conn.execute(
                        f"DELETE FROM domains WHERE company_key IN ({placeholders})",
                        company_keys,
                    )

                rows = []
                for company in companies:
                    if company.get("resolved_domain"):
                        rows.append(
                            (
                                company.get("company_key"),
                                company.get("resolved_domain"),
                                company.get("domain_source"),
                                company.get("domain_confidence"),
                                1,
                            )
                        )

                if rows:
                    conn.executemany(
                        """
                        INSERT INTO domains (
                            company_key,
                            domain,
                            source,
                            confidence,
                            is_primary
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
            if company_keys:
                session.query(Domain).filter(Domain.company_key.in_(company_keys)).delete(
                    synchronize_session=False
                )

            domains_to_insert = []
            for company in companies:
                if company.get("resolved_domain"):
                    domains_to_insert.append(
                        Domain(
                            company_key=str(company.get("company_key")),
                            domain=str(company.get("resolved_domain")),
                            source=company.get("domain_source"),
                            confidence=company.get("domain_confidence"),
                            is_primary=1,
                        )
                    )

            session.add_all(domains_to_insert)
            session.commit()

