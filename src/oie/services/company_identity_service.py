from __future__ import annotations

import re
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


LEGAL_SUFFIXES = {
    "inc",
    "inc.",
    "llc",
    "l.l.c.",
    "ltd",
    "ltd.",
    "corp",
    "corp.",
    "corporation",
    "gmbh",
    "s.a.",
    "sa",
    "s.a",
    "plc",
    "limited",
    "co",
    "co.",
}


class CompanyIdentityService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def normalize_company_name(self, company_name: str) -> str:
        value = (company_name or "").strip().lower()
        value = value.replace("&", " and ")
        value = re.sub(r"[^\w\s]", " ", value)
        tokens = [token for token in value.split() if token and token not in LEGAL_SUFFIXES]
        normalized = " ".join(tokens)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized or "unknown"

    def enrich_company_identity(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []

        for company in companies:
            display = (company.get("company") or "").strip() or "unknown"
            normalized = self.normalize_company_name(display)

            record = dict(company)
            record["company_display"] = display
            record["company_normalized"] = normalized

            enriched.append(record)

        self.ctx.metrics["companies_with_identity"] = len(enriched)
        self.ctx.metrics["company_identity_completed"] = True

        return enriched
