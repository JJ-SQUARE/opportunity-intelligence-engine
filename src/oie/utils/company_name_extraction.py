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
    "empresa confidencial",
    "confidential company",
    "world",
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
    "hiring",
    "careers",
    "career",
    "job opening",
]

WEAK_SINGLE_TOKEN_COMPANY_NAMES = {
    "world",
    "group",
    "grupo",
    "global",
    "company",
    "empresa",
    "startup",
    "holding",
    "holdings",
    "solutions",
    "services",
    "technology",
    "digital",
    "systems",
    "remote",
    "remoto",
    "latam",
    "hiring",
    "careers",
    "career",
    "vacante",
    "vacantes",
    "opportunity",
}

ATS_PATH_TOKENS = {
    "job",
    "jobs",
    "offer",
    "oferta",
    "empleo",
    "empleos",
    "careers",
    "career",
    "vacante",
    "vacantes",
    "apply",
    "application",
    "positions",
    "position",
    "opening",
    "openings",
}


BLOCKED_INFERENCE_NETLOC_TOKENS = {
    "greenhouse",
    "lever",
    "workable",
    "breezy",
    "teamtailor",
    "jobgether",
    "linkedin",
    "indeed",
    "glassdoor",
    "google",
    "gupy",
    "computrabajo",
    "talenteca",
    "jobrapido",
    "jooble",
    "sercanto",
    "elempleo",
    "hireline",
    "whatjobs",
    "expertini",
    "jobijoba",
    "pangian",
    "bumeran",
    "magneto365",
}

SNIPPET_CONTAMINATION_TERMS = {
    "apply now",
    "easy apply",
    "postulate ahora",
    "postúlate ahora",
    "solicita ahora",
    "solicitar ahora",
    "via linkedin",
    "via indeed",
    "via computrabajo",
    "via jobgether",
    "see more jobs",
    "more jobs",
    "job board",
    "portal de empleo",
    "career portal",
}


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

    lowered = candidate.lower()
    if lowered in NOISY_COMPANY_NAMES:
        return False

    if re.fullmatch(r"\d+", candidate):
        return False

    if len(candidate) < 2:
        return False

    tokens = [t for t in re.split(r"[^a-z0-9áéíóúñ]+", lowered) if t]
    if len(tokens) == 1 and tokens[0] in WEAK_SINGLE_TOKEN_COMPANY_NAMES:
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

    # Separadores ambiguos: priorizar solo lados que no huelan a rol
    for sep in [" - ", " | ", " en "]:
        if sep.lower() in text.lower():
            parts = re.split(re.escape(sep), text, flags=re.IGNORECASE)
            valid_parts = []
            for part in parts:
                candidate = _strip_noise(part)
                if not candidate:
                    continue
                if _looks_like_role_not_company(candidate):
                    continue
                if _is_valid_company_candidate(candidate):
                    valid_parts.append(candidate)

            if len(valid_parts) == 1:
                return valid_parts[0]

    if _looks_like_role_not_company(text):
        return None

    if _is_valid_company_candidate(text):
        return text

    return None


def _candidate_from_snippet(snippet: Optional[str]) -> Optional[str]:
    text = _strip_noise(snippet)
    if not text:
        return None

    lowered = text.lower()

    if any(term in lowered for term in SNIPPET_CONTAMINATION_TERMS):
        return None

    role_like_hits = sum(1 for pattern in GENERIC_ROLE_PATTERNS if pattern in lowered)
    connector_hits = lowered.count(" at ") + lowered.count(" for ") + lowered.count(" para ")
    if role_like_hits >= 2 and connector_hits >= 1:
        return None

    patterns = [
        r"(?:at|for|para)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{2,80})",
        r"empresa[: ]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9&.,'’\- ]{2,80})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _strip_noise(match.group(1))
            candidate = re.split(
                r"\s+(?:building|developing|operating|offering|providing|hiring|seeking|busca|buscando|contrata|contratando|remote|remoto|latam|mexico|méxico|colombia|peru|perú|ecuador|argentina|chile)\b|\s+[|·]|\s+-\s+|[\.,;:]",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            if _is_valid_company_candidate(candidate):
                return candidate

    return None


def _candidate_from_apply_url(apply_url: Optional[str]) -> Optional[str]:
    if not apply_url:
        return None

    try:
        parsed = urlparse(apply_url)
        path = unquote(parsed.path or "")
        netloc = (parsed.netloc or "").lower()
    except Exception:
        return None

    # No inferir marca desde ATS/job boards, wrappers o agregadores.
    if any(token in netloc for token in BLOCKED_INFERENCE_NETLOC_TOKENS):
        return None

    chunks = [chunk for chunk in path.split("/") if chunk]
    if not chunks:
        return None

    cleaned_chunks = []
    for chunk in chunks:
        chunk_text = chunk.replace("-", " ").replace("_", " ").strip()
        lowered = chunk_text.lower()
        if not lowered:
            continue
        if lowered in ATS_PATH_TOKENS:
            continue
        cleaned_chunks.append(chunk_text)

    if not cleaned_chunks:
        return None

    # Priorizar chunks cortos con pinta de marca en vez de concatenar toda la ruta.
    for raw_chunk in cleaned_chunks:
        candidate = _strip_noise(raw_chunk)
        if _is_valid_company_candidate(candidate):
            return candidate

    raw = " ".join(cleaned_chunks)
    raw = re.sub(
        r"\b(job|jobs|offer|oferta|empleo|empleos|careers|career|vacante|vacantes|apply|application|positions|position|opening|openings)\b",
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
