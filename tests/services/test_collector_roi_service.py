from oie.orchestration.run_context import RunContext
from oie.services.collector_roi_service import CollectorROIService


def test_collector_roi_service_builds_metrics():
    ctx = RunContext.create(config={}, flags={})
    service = CollectorROIService(ctx)

    unique_jobs = [
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

    duplicate_jobs = [
        {
            "source": "google_jobs",
            "job_url": "https://a.com/dup",
        }
    ]

    companies = [
        {"company_key": "cmp_a"},
        {"company_key": "cmp_b"},
    ]

    leads = [
        {"company_key": "cmp_a", "email": "eng@a.com"},
        {"company_key": "cmp_b", "email": "eng@b.com"},
    ]

    rows = service.build_roi_metrics(
        unique_jobs=unique_jobs,
        duplicate_jobs=duplicate_jobs,
        companies=companies,
        leads=leads,
    )

    assert len(rows) == 2

    google = next(row for row in rows if row["source"] == "google_jobs")
    linkedin = next(row for row in rows if row["source"] == "linkedin_serpapi")

    assert google["unique_jobs"] == 2
    assert google["duplicate_jobs"] == 1
    assert google["new_companies"] == 1
    assert google["leads_generated"] == 1

    assert linkedin["unique_jobs"] == 1
    assert linkedin["duplicate_jobs"] == 0
    assert linkedin["new_companies"] == 1
    assert linkedin["leads_generated"] == 1
