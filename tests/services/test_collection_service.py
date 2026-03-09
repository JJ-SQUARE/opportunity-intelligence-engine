from oie.orchestration.run_context import RunContext
from oie.services.collection_service import CollectionService


def test_collection_service_collects_from_enabled_google_jobs(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {
                "num_pages": 3,
                "sleep_s": 1.0,
            },
            "sources": {
                "google_jobs": {
                    "enabled": True,
                    "location_mode": "matrix",
                    "locations": ["Ecuador"],
                }
            },
            "queries": [
                {"name": "SE", "q": "desarrollador remoto"},
            ],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    google_collector = None
    for collector in service.collector_runner.registry.all():
        if collector.collector_name == "google_jobs":
            google_collector = collector
            break

    assert google_collector is not None

    def fake_load_legacy():
        def fake_collect(payload):
            assert payload["run"]["num_pages"] == 3
            assert payload["source_config"]["locations"] == ["Ecuador"]
            assert payload["queries"][0]["q"] == "desarrollador remoto"
            return [
                {
                    "title": "Python Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "job_url": "https://example.com/job/1",
                    "apply_url": "https://example.com/apply/1",
                    "description": "Python role",
                    "detected_at": "2026-03-09",
                }
            ]
        return fake_collect

    monkeypatch.setattr(google_collector, "_load_legacy_collector", fake_load_legacy)

    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "google_jobs"
    assert jobs[0]["title"] == "Python Engineer"
    assert ctx.metrics["jobs_collected_raw"] == 1
