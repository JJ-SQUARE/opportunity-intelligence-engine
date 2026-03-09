from oie.collectors.workable_ats_collector import WorkableATSCollector


def test_workable_collector_normalizes_jobs(monkeypatch):
    collector = WorkableATSCollector(
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
                    "title": "Backend Developer",
                    "company": "Omega",
                    "location": "Remote",
                    "url": "https://apply.workable.com/omega/j/123",
                    "description": "Backend role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "workable"
    assert jobs[0]["title"] == "Backend Developer"
