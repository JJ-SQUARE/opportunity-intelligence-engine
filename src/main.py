import os
from dotenv import load_dotenv

from collectors.google_jobs_serpapi import fetch_google_jobs_serpapi
from pipeline.normalize import normalize_jobs
from pipeline.dedupe import dedupe_jobs
from pipeline.aggregate import aggregate_by_company

from scoring.basic_score import basic_opportunity_score
from scoring.signals import enrich_job_with_signals
from scoring.ai_company_classifier import classify_company_with_openai

from export.to_csv import export_jobs_csv
from export.to_company_csv import export_companies_csv
from config_loader import load_config


def company_signals(company_obj):
    jobs = company_obj.get("jobs", [])

    contractor = any(j.get("is_contractor") for j in jobs)
    nearshore = any(j.get("nearshore_friendly") for j in jobs)
    remote = any(j.get("is_remote") for j in jobs) or any(
        "remote" in (j.get("location") or "").lower() for j in jobs
    )

    urgency = sum(int(j.get("urgency_hits") or 0) for j in jobs) + sum(
        1 for j in jobs if j.get("many_openings_signal")
    )

    countries = [j.get("country") for j in jobs if j.get("country")]
    country_focus = max(set(countries), key=countries.count) if countries else None

    return {
        "contractor_signal": contractor,
        "nearshore_friendly_signal": nearshore,
        "remote_friendly_signal": remote,
        "urgency_signal": urgency,
        "country_focus": country_focus,
    }


def main():
    load_dotenv()

    cfg = load_config()

    location = os.getenv("LOCATION", cfg["global"]["location"])
    num_pages = int(os.getenv("NUM_PAGES", cfg["global"]["num_pages"]))
    top_n_ai = int(os.getenv("TOP_N_AI", cfg["global"]["top_n_ai"]))

    queries = cfg["queries"]

    # 1️⃣ FETCH
    all_jobs = []
    for item in queries:
        q = item["q"]
        print(f"Fetching: {item['name']} -> {q}")
        jobs = fetch_google_jobs_serpapi(query=q, location=location, num_pages=num_pages)
        all_jobs.extend(jobs)

    jobs = all_jobs

    # 2️⃣ CLEAN
    jobs = normalize_jobs(jobs)
    jobs = dedupe_jobs(jobs)

    # 3️⃣ ENRICH JOB-LEVEL SIGNALS
    jobs = [enrich_job_with_signals(j) for j in jobs]

    os.makedirs("data/processed", exist_ok=True)
    export_jobs_csv(jobs, "data/processed/jobs_enriched.csv")
    print(f"Saved {len(jobs)} enriched jobs")

    # 4️⃣ AGGREGATE BY COMPANY
    companies = aggregate_by_company(jobs)

    # 5️⃣ COMPANY-LEVEL SIGNALS + SCORE
    scored_companies = []
    for c in companies:
        c.update(company_signals(c))
        c["score"] = basic_opportunity_score(c) + min(
            c.get("urgency_signal", 0), 8
        )
        scored_companies.append(c)

    scored_companies = sorted(
        scored_companies, key=lambda x: x["score"], reverse=True
    )

    # 6️⃣ OPTIONAL AI CLASSIFICATION (TOP N ONLY)
    for c in scored_companies[:top_n_ai]:
        ai = classify_company_with_openai(c["company"], c)
        c["company_type_ai"] = ai.get("company_type")
        c["industry_ai"] = ai.get("industry")
        c["vendor_acceptance_probability_ai"] = ai.get(
            "vendor_acceptance_probability"
        )
        c["notes_ai"] = ai.get("notes")
    out_companies = export_companies_csv(scored_companies, "data/processed/companies_scored.csv")
    print(f"Saved companies to {out_companies}")

    # 7️⃣ EXPORT COMPANIES
    out_companies = export_companies_csv(
        scored_companies,
        "data/processed/companies_scored.csv",
    )
    print(f"Saved companies to {out_companies}")

    # 8️⃣ Print top results
    print("\nTop Opportunities:")
    for c in scored_companies[:10]:
        print(
            f"{c['company']} | "
            f"Openings: {c['total_openings']} | "
            f"Score: {c['score']} | "
            f"Country: {c.get('country_focus')}"
        )


if __name__ == "__main__":
    main()