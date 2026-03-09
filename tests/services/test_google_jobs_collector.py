from oie.collectors.google_jobs_collector import GoogleJobsCollector


def test_google_jobs_collector_normalizes_legacy_jobs(monkeypatch):
    collector = GoogleJobsCollector(
        config={
            "queries": [{"name": "SE", "q": "python developer remote"}],
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "source_config": {
                "enabled": True,
                "location_mode": "matrix",
                "locations": ["Ecuador"],
            },
        }
    )

    def fake_load_legacy():
        def fake_collect(payload):
            return [
                {
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "job_url": "https://example.com/job/1",
                    "apply_url": "https://example.com/apply/1",
                    "description": "Python role",
                    "detected_at": "2026-03-09",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "google_jobs"
    assert jobs[0]["title"] == "Backend Engineer"
