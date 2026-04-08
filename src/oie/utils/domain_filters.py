from __future__ import annotations

from urllib.parse import urlparse


JOB_BOARD_DOMAINS = {
    "linkedin.com",
    "jooble.org",
    "indeed.com",
    "talent.com",
    "sercanto.com",
    "computrabajo.com",
    "recruit.net",
    "bebee.com",
    "jobrapido.com",
    "mifuturoempleo.com",
    "occ.com.mx",
    "elempleo.com",
    "hireline.io",
    "hireline.com",
    "whatjobs.com",
    "expertini.com",
    "jobijoba.com",
    "jobgether.com",
    "pangian.com",
}


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""

    raw = value.strip().lower()
    if not raw:
        return ""

    if "://" in raw:
        raw = urlparse(raw).netloc.lower()

    if raw.startswith("www."):
        raw = raw[4:]

    return raw.strip(".")


def is_job_board_domain(domain: str | None) -> bool:
    d = normalize_domain(domain)
    if not d:
        return False

    return any(d == blocked or d.endswith(f".{blocked}") for blocked in JOB_BOARD_DOMAINS)
