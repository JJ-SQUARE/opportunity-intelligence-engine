from oie.collectors.greenhouse_ats_collector import GreenhouseATSCollector


def test_greenhouse_collector_normalizes_jobs(monkeypatch):
    collector = GreenhouseATSCollector(
        config={
            "queries": [{"q": "python developer"}],
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "source_config": {"enabled": True},
        }
    )

    def fake_loader():
        def fake_collect(**kwargs):
            return [
                {
                    "title": "Platform Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://boards.greenhouse.io/acme/jobs/123",
                    "description": "Infra role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "greenhouse"
    assert jobs[0]["title"] == "Platform Engineer"
