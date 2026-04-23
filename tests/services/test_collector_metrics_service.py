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

def test_collector_metrics_service_includes_effective_counts():
    ctx = RunContext.create(config={}, flags={})
    service = CollectorMetricsService(ctx)

    jobs = [
        {"source": "google_jobs", "company_key": "a"},
        {"source": "google_jobs", "company_key": "missing"},
        {"source": "linkedin_serpapi", "company_key": "b"},
    ]

    companies = [
        {"company_key": "a"},
        {"company_key": "b"},
    ]

    metrics = service.build_metrics(jobs, companies)

    google = next(m for m in metrics if m["source"] == "google_jobs")
    assert google["jobs_collected"] == 2
    assert google["jobs_effective"] == 1
    assert google["effective_companies"] == 1
    assert google["job_effectiveness_rate"] == 0.5
    assert ctx.metrics["collector_metrics_rows"] == 2

