from oie.collectors.static_jobs_collector import StaticJobsCollector
from oie.orchestration.run_context import RunContext
from oie.services.collector_runner_service import CollectorRunnerService


def test_collector_runner_service_runs_enabled_collectors():
    ctx = RunContext.create(config={}, flags={})
    service = CollectorRunnerService(ctx)

    collector = StaticJobsCollector(
        config={
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "job_url": "https://acme.com/jobs/1",
                    "apply_url": "https://acme.com/apply/1",
                    "description": "Python role",
                    "detected_at": "2026-03-09",
                }
            ]
        }
    )

    service.register_collectors([collector])
    jobs = service.run_enabled_collectors(enabled_names=["static_jobs"])

    assert len(jobs) == 1
    assert jobs[0]["source"] == "static_jobs"
    assert ctx.metrics["collector_static_jobs_jobs_collected"] == 1
    assert ctx.metrics["collectors_total_jobs_collected"] == 1
