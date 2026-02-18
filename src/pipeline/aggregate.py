from typing import Dict, List, Any
from collections import defaultdict


def aggregate_by_company(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    companies = defaultdict(list)

    for job in jobs:
        if job.get("company"):
            companies[job["company"]].append(job)

    aggregated = []

    for company, company_jobs in companies.items():
        aggregated.append(
            {
                "company": company,
                "total_openings": len(company_jobs),
                "locations": list({j.get("location") for j in company_jobs if j.get("location")}),
                "titles": list({j.get("job_title") for j in company_jobs if j.get("job_title")}),
                "jobs": company_jobs,
            }
        )

    return aggregated