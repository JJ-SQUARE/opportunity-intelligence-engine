from oie.services.collector_metrics_service import CollectorMetricsService
from oie.orchestration.run_context import RunContext


def test_collector_metrics_service_builds_metrics():

    ctx = RunContext.create(config={}, flags={})

    service = CollectorMetricsService(ctx)

    jobs = [
        {"source": "google_jobs", "company_key": "a"},
        {"source": "google_jobs", "company_key": "a"},
        {"source": "linkedin_serpapi", "company_key": "b"},
        {"source": "linkedin_serpapi", "company_key": "c"},
    ]

    companies = [
        {"company_key": "a"},
        {"company_key": "b"},
        {"company_key": "c"},
    ]

    metrics = service.build_metrics(jobs, companies)

    assert len(metrics) == 2

    google = next(m for m in metrics if m["source"] == "google_jobs")

    assert google["jobs_collected"] == 2
    assert google["unique_companies"] == 1
