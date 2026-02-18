import os
from dotenv import load_dotenv

from collectors.google_jobs_serpapi import fetch_google_jobs_serpapi
from pipeline.normalize import normalize_jobs
from pipeline.dedupe import dedupe_jobs
from export.to_csv import export_jobs_csv
from pipeline.aggregate import aggregate_by_company
from scoring.basic_score import basic_opportunity_score
from scoring.signals import enrich_job_with_signals

def main():
    load_dotenv()

    query = os.getenv("QUERY", "Angular Developer contract remote")
    location = os.getenv("LOCATION", "United States")
    num_pages = int(os.getenv("NUM_PAGES", "3"))

    jobs = fetch_google_jobs_serpapi(query=query, location=location, num_pages=num_pages)
    jobs = normalize_jobs(jobs)
    jobs = dedupe_jobs(jobs)
    jobs = [enrich_job_with_signals(j) for j in jobs]
    out_path_jobs = export_jobs_csv(jobs, "data/processed/jobs_enriched.csv")
    print(f"Saved {len(jobs)} enriched jobs to {out_path_jobs}")

    companies = aggregate_by_company(jobs)

    scored_companies = []

    for company in companies:
        company["score"] = basic_opportunity_score(company)
        scored_companies.append(company)

    scored_companies = sorted(scored_companies, key=lambda x: x["score"], reverse=True)

    for c in scored_companies[:10]:
        print(f"{c['company']} | Openings: {c['total_openings']} | Score: {c['score']}")

    os.makedirs("data/processed", exist_ok=True)
    out_path = export_jobs_csv(jobs, "data/processed/jobs.csv")

    print(f"Saved {len(jobs)} jobs to {out_path}")


if __name__ == "__main__":
    main()