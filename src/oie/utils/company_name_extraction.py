from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse, unquote

from oie.utils.company_identity_utils import is_actionable_company_name


NOISY_COMPANY_NAMES = {
    "confidencial",
    "confidential",
    "importante empresa",
    "empresa del sector",
    "anonymous",
    "anonimo",
    "anónimo",
}

GENERIC_ROLE_PATTERNS = [
    "engineer",
    "developer",
    "desarrollador",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "data engineer",
    "software engineer",
    "arquitecto",
    "analyst",
    "analista",
    "manager",
    "qa",
    "tester",
    "remote role",
    "vacante",
    "opportunity",
]


def _clean_text(value: Optional[str]) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_noise(value: Optional[str]) -> str:
    text = _clean_text(value)
    text = re.sub(r"^\[.*?\]\s*", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -|,:;")
    return text.strip()


def _looks_like_role_not_company(value: Optional[str]) -> bool:
    text = _strip_noise(value).lower()
    if not text:
        return True
    return any(pattern in text for pattern in GENERIC_ROLE_PATTERNS)


def _is_valid_company_candidate(value: Optional[str]) -> bool:
    candidate = _strip_noise(value)
    if not candidate:
        return False
    if candidate.lower() in NOISY_COMPANY_NAMES:
        return False
    if re.fullmatch(r"\d+", candidate):
        return False
    if len(candidate) < 2:
        return False
    if _looks_like_role_not_company(candidate):
        return False
    return is_actionable_company_name(candidate)


def _candidate_from_title(title: Optional[str]) -> Optional[str]:
    text = _strip_noise(title)
    if not text:
        return None

    # Patrones directos tipo "Backend Engineer at Tenaris"
    direct_patterns = [
        r"\bat\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{1,80})$",
        r"\bfor\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{1,80})$",
        r"\bpara\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{1,80})$",
        r"\b@\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{1,80})$",
    ]

    for pattern in direct_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _strip_noise(match.group(1))
            if _is_valid_company_candidate(candidate):
                return candidate

    # Separadores más ambiguos
    for sep in [" - ", " | ", " en "]:
        if sep.lower() in text.lower():
            parts = re.split(re.escape(sep), text, flags=re.IGNORECASE)
            for part in parts:
                candidate = _strip_noise(part)
                if _is_valid_company_candidate(candidate):
                    return candidate

    if _is_valid_company_candidate(text):
        return text

    return None


def _candidate_from_snippet(snippet: Optional[str]) -> Optional[str]:
    text = _strip_noise(snippet)
    if not text:
        return None

    patterns = [
        r"(?:at|for|para)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{2,80})",
        r"empresa[: ]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{2,80})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _strip_noise(match.group(1))
            if _is_valid_company_candidate(candidate):
                return candidate

    return None


def _candidate_from_apply_url(apply_url: Optional[str]) -> Optional[str]:
    if not apply_url:
        return None

    try:
        parsed = urlparse(apply_url)
        path = unquote(parsed.path or "")
    except Exception:
        return None

    chunks = [chunk for chunk in path.split("/") if chunk]
    if not chunks:
        return None

    raw = " ".join(chunks)
    raw = raw.replace("-", " ").replace("_", " ")
    raw = re.sub(
        r"\b(job|jobs|offer|oferta|empleo|careers|career|vacante|vacantes|apply)\b",
        " ",
        raw,
        flags=re.IGNORECASE,
    )
    raw = re.sub(r"\s+", " ", raw).strip()

    if not raw:
        return None

    candidate = _strip_noise(raw)
    if _is_valid_company_candidate(candidate):
        return candidate

    return None


def extract_actionable_company_name(
    company_display: Optional[str],
    title: Optional[str] = None,
    snippet: Optional[str] = None,
    apply_url: Optional[str] = None,
) -> Optional[str]:
    cleaned_display = _strip_noise(company_display)
    if _is_valid_company_candidate(cleaned_display):
        return cleaned_display

    for candidate in (
        _candidate_from_title(title),
        _candidate_from_snippet(snippet),
        _candidate_from_apply_url(apply_url),
    ):
        if _is_valid_company_candidate(candidate):
            return _strip_noise(candidate)

    return None
