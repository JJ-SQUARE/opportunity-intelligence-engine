import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

ATS_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "icims.com",
    "ashbyhq.com",
    "jobvite.com",
    "smartrecruiters.com",
    "successfactors.com",
    "taleo.net",
    "bamboohr.com",
}

def _text(job: Dict[str, Any]) -> str:
    parts = [
        job.get("job_title") or "",
        job.get("description") or "",
        job.get("location") or "",
        job.get("via") or "",
        job.get("url") or "",
    ]
    return " ".join(parts).lower()

def detect_contract_type(job: Dict[str, Any]) -> Dict[str, bool]:
    t = _text(job)

    contractor = bool(re.search(r"\b(contract|contractor|1099|freelance|temp|temporary|part[- ]time)\b", t))
    full_time = bool(re.search(r"\b(full[- ]time|permanent|w-2)\b", t))

    # Si aparecen ambos, lo dejamos como contractor=True (señal de flexibilidad)
    return {"is_contractor": contractor, "is_full_time": full_time}

def detect_remote_nearshore(job: Dict[str, Any]) -> Dict[str, bool]:
    t = _text(job)

    is_remote = bool(re.search(r"\b(remote|work from home|wfh)\b", t))
    # Señales explícitas
    nearshore = bool(re.search(r"\b(nearshore|latam|latin america|mexico|colombia|peru|argentina|brazil|chile)\b", t))
    offshore = bool(re.search(r"\b(offshore|india|philippines|pakistan)\b", t))

    # “US only” o “must be in US” suele bajar probabilidad nearshore
    us_only = bool(re.search(r"\b(us only|must be in the us|within the us|u\.s\. only)\b", t))

    return {
        "is_remote": is_remote,
        "nearshore_friendly": nearshore and not us_only,
        "offshore_mentioned": offshore,
        "us_only": us_only,
    }

def detect_urgency(job: Dict[str, Any]) -> Dict[str, Any]:
    t = _text(job)
    urgency_terms = [
        r"\burgent\b",
        r"\basap\b",
        r"\bimmediate\b",
        r"\bstarting (immediately|asap)\b",
        r"\bfill (quickly|fast)\b",
        r"\binterviews? (this week|next week)\b",
    ]
    urgency_hits = sum(1 for p in urgency_terms if re.search(p, t))
    many_openings_signal = bool(re.search(r"\b(multiple openings|hiring (multiple|several)|several positions)\b", t))

    return {
        "urgency_hits": urgency_hits,
        "many_openings_signal": many_openings_signal,
    }

def infer_country(job: Dict[str, Any]) -> Optional[str]:
    loc = (job.get("location") or "").lower()

    # Muy simple al inicio: lo refinamos luego
    if "united states" in loc or re.search(r"\b(usa|u\.s\.|us)\b", loc):
        return "US"
    if "canada" in loc:
        return "CA"
    if "mexico" in loc:
        return "MX"
    if "colombia" in loc:
        return "CO"
    if "peru" in loc:
        return "PE"
    if "argentina" in loc:
        return "AR"
    if "brazil" in loc or "brasil" in loc:
        return "BR"
    if "chile" in loc:
        return "CL"
    if "uk" in loc or "united kingdom" in loc or "england" in loc:
        return "UK"
    if "spain" in loc or "españa" in loc:
        return "ES"

    # “Remote” sin país explícito
    if "remote" in loc:
        return None

    return None

def infer_company_domain_from_url(url: Optional[str]) -> Optional[str]:
    """
    Best-effort:
    - Si el apply link NO es un ATS conocido y parece dominio de empresa → usarlo
    - Si es ATS → None (luego lo resolveremos vía Hunter/Apollo)
    """
    if not url:
        return None

    try:
        host = urlparse(url).hostname or ""
        host = host.lower().replace("www.", "")
        if not host:
            return None
        # ATS conocidos
        if any(host.endswith(d) for d in ATS_DOMAINS):
            return None
        # dominios muy genéricos (indeed, linkedin, etc.)
        if any(x in host for x in ["linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com"]):
            return None
        return host
    except Exception:
        return None

def enrich_job_with_signals(job: Dict[str, Any]) -> Dict[str, Any]:
    contract = detect_contract_type(job)
    remote = detect_remote_nearshore(job)
    urgency = detect_urgency(job)
    country = infer_country(job)
    domain_guess = infer_company_domain_from_url(job.get("url"))

    out = dict(job)
    out.update(contract)
    out.update(remote)
    out.update(urgency)
    out["country"] = country
    out["domain_guess"] = domain_guess
    return out