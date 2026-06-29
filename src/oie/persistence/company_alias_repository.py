from __future__ import annotations

from typing import Any, Dict, List, Optional

from oie.persistence.models import Company, CompanyAlias
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


class CompanyAliasRepository(RepositoryBase):
    def replace_aliases(self, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
                if company_keys:
                    placeholders = ",".join("?" for _ in company_keys)
                    conn.execute(
                        f"DELETE FROM company_aliases WHERE company_key IN ({placeholders})",
                        company_keys,
                    )

                rows = []
                for company in companies:
                    company_key = company.get("company_key")
                    aliases = company.get("aliases", []) or []
                    alias_type_map = company.get("alias_type_map", {}) or {}
                    for alias in aliases:
                        rows.append(
                            (
                                company_key,
                                alias,
                                alias_type_map.get(alias, company.get("company_normalized")),
                                alias_type_map.get(f"{alias}__type", "observed_name"),
                            )
                        )

                if rows:
                    conn.executemany(
                        """
                        INSERT INTO company_aliases (
                            company_key,
                            alias_value,
                            alias_normalized,
                            alias_type
                        )
                        VALUES (?, ?, ?, ?)
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
                session.query(CompanyAlias).filter(CompanyAlias.company_key.in_(company_keys)).delete(
                    synchronize_session=False
                )

            aliases_to_insert = []
            for company in companies:
                company_key = company.get("company_key")
                aliases = company.get("aliases", []) or []
                alias_type_map = company.get("alias_type_map", {}) or {}
                for alias in aliases:
                    aliases_to_insert.append(
                        CompanyAlias(
                            company_key=str(company_key),
                            alias_value=str(alias),
                            alias_normalized=str(alias_type_map.get(alias, company.get("company_normalized")) or ""),
                            alias_type=str(alias_type_map.get(f"{alias}__type", "observed_name") or "observed_name"),
                        )
                    )

            session.add_all(aliases_to_insert)
            session.commit()

    def find_company_by_alias_normalized(self, alias_normalized: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT c.company_key, c.company_display, c.company_normalized, c.resolved_domain
                    FROM company_aliases a
                    JOIN companies c ON c.company_key = a.company_key
                    WHERE a.alias_normalized = ?
                    LIMIT 1
                    """,
                    (alias_normalized,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            row = (
                session.query(Company)
                .join(CompanyAlias, CompanyAlias.company_key == Company.company_key)
                .filter(CompanyAlias.alias_normalized == alias_normalized)
                .first()
            )
            if row is None:
                return None
            return {
                "company_key": row.company_key,
                "company_display": row.company_display,
                "company_normalized": row.company_normalized,
                "resolved_domain": row.resolved_domain,
            }

