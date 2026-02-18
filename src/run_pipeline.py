import os
from typing import Any, Dict, List

from collectors.google_jobs_serpapi import fetch_google_jobs_serpapi
from pipeline.normalize import normalize_jobs
from pipeline.dedupe import dedupe_jobs
from pipeline.aggregate import aggregate_by_company

from scoring.signals import enrich_job_with_signals
from scoring.basic_score import basic_opportunity_score
from scoring.ai_company_classifier import classify_company_with_llm

from export.to_csv import export_jobs_csv
from export.to_company_csv import export_companies_csv


def company_signals(company_obj):
    jobs = company_obj.get("jobs", [])

    contractor = any(j.get("is_contractor") for j in jobs)

    # Remote signals
    remote = any(j.get("is_remote") for j in jobs) or any(
        "remote" in (j.get("location") or "").lower() for j in jobs
    )

    us_only = any(j.get("us_only") for j in jobs)

    # Nearshore-friendly: explícito nearshore/latam + no US-only
    nearshore = any(j.get("nearshore_friendly") for j in jobs) and not us_only

    urgency = sum(int(j.get("urgency_hits") or 0) for j in jobs) + sum(
        1 for j in jobs if j.get("many_openings_signal")
    )

    countries = [j.get("country") for j in jobs if j.get("country")]
    country_focus = max(set(countries), key=countries.count) if countries else None

    return {
        "contractor_signal": contractor,
        "remote_friendly_signal": remote,
        "us_only_signal": us_only,
        "nearshore_friendly_signal": nearshore,
        "urgency_signal": urgency,
        "country_focus": country_focus,
    }

def fetch_jobs_from_config(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    run_cfg = cfg.get("run", {})
    num_pages = int(run_cfg.get("num_pages", 3))
    sleep_s = float(run_cfg.get("sleep_s", 1.0))

    sources = cfg.get("sources", {})
    google_jobs_cfg = sources.get("google_jobs", {})
    if not google_jobs_cfg.get("enabled", True):
        return []

    locations = google_jobs_cfg.get("locations", ["United States"])
    queries = cfg.get("queries", [])

    # Fallback válido para SerpApi cuando loc = "Remote"
    remote_fallback_location = google_jobs_cfg.get("remote_fallback_location", "United States")

    all_jobs: List[Dict[str, Any]] = []

    for q in queries:
        q_name = q.get("name", "query")
        q_text = q.get("q", "")

        for loc in locations:
            serp_location = loc
            serp_query = q_text

            # "Remote" NO es location válido para google_jobs en SerpApi
            if isinstance(loc, str) and loc.strip().lower() == "remote":
                serp_location = remote_fallback_location
                if "remote" not in (serp_query or "").lower():
                    serp_query = f"{serp_query} remote"

            try:
                batch = fetch_google_jobs_serpapi(
                    query=serp_query,
                    location=serp_location,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                )
            except Exception as e:
                print(
                    f"[WARN] Failed fetch | query='{q_name}' | loc='{loc}' "
                    f"(serp_location='{serp_location}') | {type(e).__name__}: {e}"
                )
                continue

            for j in batch:
                j["query_name"] = q_name
                j["query_text"] = q_text
                j["search_location"] = loc
                j["serp_location_used"] = serp_location
                j["serp_query_used"] = serp_query

            all_jobs.extend(batch)

    return all_jobs


def run(cfg: Dict[str, Any]) -> Dict[str, Any]:
    outputs = cfg.get("outputs", {})
    jobs_csv = outputs.get("jobs_csv", "data/processed/jobs_enriched.csv")
    companies_csv = outputs.get("companies_csv", "data/processed/companies_scored.csv")

    os.makedirs("data/processed", exist_ok=True)

    # 1) Fetch
    jobs = fetch_jobs_from_config(cfg)

    # 2) Normalize + dedupe
    jobs = normalize_jobs(jobs)
    jobs = dedupe_jobs(jobs)

    # 3) Enrich job signals
    jobs = [enrich_job_with_signals(j) for j in jobs]

    export_jobs_csv(jobs, jobs_csv)

    # 4) Aggregate + score
    companies = aggregate_by_company(jobs)

    scored = []
    for c in companies:
        c.update(company_signals(c))
        score = basic_opportunity_score(c) + min(c.get("urgency_signal", 0), 8)

        if c.get("contractor_signal"):
            score += 2

        if c.get("remote_friendly_signal") and not c.get("us_only_signal"):
            score += 2

        if c.get("nearshore_friendly_signal"):
            score += 3

        if c.get("us_only_signal"):
            score -= 3

        c["score"] = round(score, 2)
        scored.append(c)

    scored = sorted(scored, key=lambda x: x["score"], reverse=True)

    # 5) LLM classification (optional)
    llm_cfg = cfg.get("llm", {})
    if llm_cfg.get("enabled", True):
        top_n = int(llm_cfg.get("top_n", 10))
        provider = llm_cfg.get("provider", "openai")
        model = llm_cfg.get("model", "gpt-4.1-mini")
        temperature = float(llm_cfg.get("temperature", 0.2))
        cache_path = llm_cfg.get("cache_path", "data/processed/company_ai_cache.json")

        for c in scored[:top_n]:
            ai = classify_company_with_llm(
                company=c["company"],
                context=c,
                provider=provider,
                model=model,
                temperature=temperature,
                cache_path=cache_path,
            )
            c["company_type_ai"] = ai.get("company_type")
            c["industry_ai"] = ai.get("industry")
            c["vendor_acceptance_probability_ai"] = ai.get("vendor_acceptance_probability")
            c["nearshore_friendly_ai"] = ai.get("nearshore_friendly")
            c["remote_friendly_ai"] = ai.get("remote_friendly")
            c["notes_ai"] = ai.get("notes")

    out_companies = export_companies_csv(scored, companies_csv)

    return {
        "jobs_count": len(jobs),
        "companies_count": len(scored),
        "jobs_csv": jobs_csv,
        "companies_csv": out_companies,
        "top_companies": scored[:10],
    }