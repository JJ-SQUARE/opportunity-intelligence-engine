from oie.collectors.lever_ats_collector import LeverATSCollector


def test_lever_collector_normalizes_jobs(monkeypatch):
    collector = LeverATSCollector(
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
                    "title": "Software Engineer",
                    "company": "Gamma",
                    "location": "Remote",
                    "url": "https://jobs.lever.co/gamma/123",
                    "description": "Backend role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "lever"
    assert jobs[0]["title"] == "Software Engineer"
