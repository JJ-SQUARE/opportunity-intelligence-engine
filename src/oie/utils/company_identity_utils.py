from __future__ import annotations

import re
from typing import Optional


NON_ACTIONABLE_COMPANY_NAMES = {
    "",
    "unknown",
    "n/a",
    "na",
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
    "empresa confidencial",
    "confidential company",
    "stealth company",
    "stealth startup company",
    "world",
    "company",
    "empresa",
    "startup",
    "grupo",
    "group",
    "hiring",
    "careers",
    "career",
    "job opening",
    "job openings",
    "vacante",
    "vacantes",
    "opportunity",
    "remote",
    "remoto",
    "latam",
}

WEAK_SINGLE_TOKENS = {
    "world",
    "global",
    "group",
    "grupo",
    "company",
    "empresa",
    "startup",
    "holding",
    "holdings",
    "solutions",
    "solution",
    "services",
    "service",
    "technology",
    "technologies",
    "digital",
    "systems",
    "system",
    "consulting",
    "consultoria",
    "consultoría",
    "labs",
    "lab",
    "team",
    "remote",
    "remoto",
    "latam",
}

COMMON_PERSON_FIRST_NAMES = {
    "juan", "jose", "josé", "maria", "maría", "carlos", "luis", "pedro",
    "jorge", "andres", "andrés", "miguel", "diego", "daniel", "david",
    "ana", "laura", "sofia", "sofía", "valentina", "camila", "natalia",
    "fernando", "ricardo", "roberto", "alejandro", "gabriel",
}


NOISY_PATTERNS = (
    r"^remote\b",
    r"^remoto\b",
    r"^confidential\b",
    r"^confidencial\b",
    r"^stealth\b",
    r"^hiring\b",
    r"^careers?\b",
    r"^job openings?\b",
    r"^vacantes?\b",
    r"^opportunit(?:y|ies)\b",
    r"^senior\b",
    r"^sr\b",
    r"^semi senior\b",
    r"^semi-senior\b",
    r"^junior\b",
    r"^jr\b",
    r"^mid\b",
)


def normalize_company_name(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def _tokenize(value: Optional[str]) -> list[str]:
    normalized = normalize_company_name(value)
    if not normalized:
        return []
    return [t for t in re.split(r"[^a-z0-9áéíóúñ]+", normalized) if t]


def _looks_like_person_name(value: Optional[str]) -> bool:
    tokens = _tokenize(value)
    if len(tokens) not in {2, 3}:
        return False
    if tokens[0] not in COMMON_PERSON_FIRST_NAMES:
        return False
    if any(token in WEAK_SINGLE_TOKENS for token in tokens[1:]):
        return False
    return True


def is_non_actionable_company_name(value: Optional[str]) -> bool:
    normalized = normalize_company_name(value)
    if not normalized:
        return True

    if normalized in NON_ACTIONABLE_COMPANY_NAMES:
        return True

    if any(re.match(pattern, normalized) for pattern in NOISY_PATTERNS):
        return True

    blocked_prefixes = (
        "confidencial ",
        "confidential ",
        "importante empresa ",
        "empresa del sector ",
        "empresa lider ",
        "empresa líder ",
        "empresa confidencial ",
        "confidential company ",
        "stealth company ",
        "hiring ",
        "career ",
        "careers ",
        "job opening ",
        "job openings ",
        "vacante ",
        "vacantes ",
        "opportunity ",
    )
    if normalized.startswith(blocked_prefixes):
        return True

    # 🚫 Rechazar nombres con alta ambigüedad estructural
    ambiguous_patterns = (
        r".*empresa.*sector.*",
        r".*compañ[ií]a.*sector.*",
        r".*company.*sector.*",
        r".*leading company.*",
        r".*fast growing company.*",
        r".*startup stealth.*",
        r".*stealth.*startup.*",
    )
    if any(re.match(pattern, normalized) for pattern in ambiguous_patterns):
        return True

    tokens = _tokenize(normalized)
    if not tokens:
        return True

    if len(tokens) == 1 and tokens[0] in WEAK_SINGLE_TOKENS:
        return True

    if _looks_like_person_name(normalized):
        return True

    return False


def is_actionable_company_name(value: Optional[str]) -> bool:
    return not is_non_actionable_company_name(value)
