from oie.orchestration.run_context import RunContext
from oie.services.collector_contribution_service import CollectorContributionService


def test_collector_contribution_service_builds_metrics():
    ctx = RunContext.create(config={}, flags={})
    service = CollectorContributionService(ctx)

    jobs = [
        {
            "source": "google_jobs",
            "company_key": "cmp_a",
            "job_url": "https://a.com/1",
        },
        {
            "source": "google_jobs",
            "company_key": "cmp_a",
            "job_url": "https://a.com/2",
        },
        {
            "source": "linkedin_serpapi",
            "company_key": "cmp_b",
            "job_url": "https://b.com/1",
        },
    ]

    companies = [
        {"company_key": "cmp_a"},
        {"company_key": "cmp_b"},
    ]

    leads = [
        {
            "company_key": "cmp_a",
            "email": "eng@a.com",
        },
        {
            "company_key": "cmp_b",
            "email": "eng@b.com",
        },
    ]

    rows = service.build_contribution_metrics(jobs, companies, leads)

    assert len(rows) == 2

    google = next(row for row in rows if row["source"] == "google_jobs")
    linkedin = next(row for row in rows if row["source"] == "linkedin_serpapi")

    assert google["jobs_collected"] == 2
    assert google["unique_jobs"] == 2
    assert google["new_companies"] == 1
    assert google["leads_generated"] == 1

    assert linkedin["jobs_collected"] == 1
    assert linkedin["new_companies"] == 1
