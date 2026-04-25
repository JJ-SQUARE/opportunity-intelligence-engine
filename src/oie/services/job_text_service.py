from __future__ import annotations

import re
from typing import Any, Dict, List


TECH_HINTS = [
    ".net", "react", "angular", "vue", "node", "node.js", "python", "fastapi",
    "java", "spring", "aws", "azure", "gcp", "sql", "mysql", "postgres",
    "graphql", "rest", "microservices", "docker", "kubernetes", "aem",
    "javascript", "typescript", "php", "c#", "ai", "gemini", "codex",
]

SUSPICIOUS_DESCRIPTION_MARKERS = (
    " ...",
    "expand",
    "hace ",
    "há ",
    "ago",
    "job summary",
    "platform support engineer",
)


def normalize_match_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9+#\.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_match_tokens(title: str) -> List[str]:
    stopwords = {
        "the", "and", "for", "with", "from", "at", "para", "con", "del", "las", "los",
        "remote", "remoto", "latam", "software", "engineer", "developer", "desarrollador",
        "senior", "sênior", "sr", "lead", "mid", "level", "full", "time",
    }
    normalized = normalize_match_text(title)
    tokens: List[str] = []
    for token in normalized.split():
        if len(token) <= 2:
            continue
        if token in stopwords:
            continue
        if token.isdigit():
            continue
        tokens.append(token)

    deduped: List[str] = []
    seen = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped[:8]


def description_looks_contaminated(job: Dict[str, Any]) -> bool:
    description = normalize_match_text(job.get("description", ""))
    title = str(job.get("title", "") or "")
    source = str(job.get("source", "") or "").strip().lower()

    if not description:
        return True

    title_tokens = title_match_tokens(title)
    if not title_tokens:
        return False

    token_hits = sum(1 for token in title_tokens if token in description)
    suspicious_hits = sum(1 for marker in SUSPICIOUS_DESCRIPTION_MARKERS if marker in description)

    # No descartamos descripciones cortas legítimas sin source o de fuentes internas/tests.
    # El filtro agresivo aplica solo a snippets SERP/low-trust o cuando hay marcadores claros.
    if token_hits == 0 and source in {"linkedin_serpapi", "google_jobs"} and len(title_tokens) >= 2:
        return True

    if token_hits == 0 and suspicious_hits >= 1:
        return True

    return False


def safe_job_description(job: Dict[str, Any]) -> str:
    description = " ".join(str(job.get("description", "") or "").split()).strip()
    if not description:
        return ""
    if description_looks_contaminated(job):
        return ""
    return description


def extract_budget(text: str) -> str:
    value = (text or "").replace("\n", " ")
    patterns = [
        r"(USD\s?\$?\s?[\d,]+(?:\s?-\s?USD\s?\$?\s?[\d,]+)?)",
        r"(\$\s?[\d,]+(?:\s?-\s?\$\s?[\d,]+)?)",
        r"(MXN\s?\$?\s?[\d,]+(?:\s?-\s?MXN\s?\$?\s?[\d,]+)?)",
        r"(S/\.\s?[\d,]+(?:\s?-\s?S/\.\s?[\d,]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_techs(text: str, limit: int = 6) -> str:
    lowered = (text or "").lower()
    found = []
    for hint in TECH_HINTS:
        if hint.lower() in lowered:
            found.append(hint)

    deduped = []
    seen = set()
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return ", ".join(deduped[:limit])


def truncate_text(text: str, limit: int = 260) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_job_summary(job: Dict[str, Any]) -> str:
    workplace = []
    if job.get("is_remote"):
        workplace.append("remote")
    if job.get("is_full_time"):
        workplace.append("full-time")
    if job.get("is_contractor"):
        workplace.append("contractor")
    workplace_text = ", ".join(workplace) if workplace else "N/D"

    description = safe_job_description(job)
    text_for_extraction = " ".join([str(job.get("title", "") or ""), description])

    budget = extract_budget(description) or "No detectado"
    techs = extract_techs(text_for_extraction) or "No detectadas"

    if description:
        summary_text = truncate_text(description)
    else:
        summary_text = (
            f"Descripción no confiable desde {job.get('source') or 'fuente desconocida'}; "
            f"usar título, URL y apply URL para validación manual."
        )

    return (
        f"{job.get('title', 'Sin título')}. "
        f"Ubicación: {job.get('location') or 'N/D'}. "
        f"Modalidad: {workplace_text}. "
        f"Budget: {budget}. "
        f"Skills/stack detectados: {techs}. "
        f"Resumen: {summary_text}"
    )
