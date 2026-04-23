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
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "teamtailor.com",
    "breezy.hr",
    "boards.greenhouse.io",
    "jobs.lever.co",
    "apply.workable.com",
    "jobs.teamtailor.com",
    "app.breezy.hr",
    "gupy.io",
    "google.com",
    "t.co",
    "bit.ly",
    "goo.gl",
    "lnkd.in",
    "glassdoor.com",
    "ziprecruiter.com",
    "grabjobs.co",
    "talenteca.com",
    "jobleads.com",
    "oficinaempleo.com",
    "quierolaburo.com",
    "magneto365.com",
    "bumeran.com",
    "buscojobs.com",
    "buscojobs.com.ec",
    "multitrabajos.com",
    "vacantesdigitales.com",
    "trabajosdiarios.com",
    "jobisjob.com",
    "jobilize.com",
    "adzuna.com",
    "monster.com",
    "careerjet.com",
    "jobtoday.com",
    "learn4good.com",
    "lensa.com",
    "wellfound.com",
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
