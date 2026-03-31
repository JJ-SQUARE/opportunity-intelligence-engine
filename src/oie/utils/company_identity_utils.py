from __future__ import annotations

from typing import Optional


NON_ACTIONABLE_COMPANY_NAMES = {
    "confidencial",
    "confidential",
    "importante empresa",
    "empresa del sector",
    "empresa lider",
    "empresa líder",
    "stealth",
    "stealth startup",
    "anonymous",
    "anonimo",
    "anónimo",
    "importante empresa del sector",
}


def normalize_company_name(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def is_non_actionable_company_name(value: Optional[str]) -> bool:
    normalized = normalize_company_name(value)
    if not normalized:
        return True

    if normalized in NON_ACTIONABLE_COMPANY_NAMES:
        return True

    blocked_prefixes = (
        "confidencial ",
        "confidential ",
        "importante empresa ",
        "empresa del sector ",
        "empresa lider ",
        "empresa líder ",
    )
    return normalized.startswith(blocked_prefixes)


def is_actionable_company_name(value: Optional[str]) -> bool:
    return not is_non_actionable_company_name(value)
