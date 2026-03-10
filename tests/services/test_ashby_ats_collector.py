from oie.collectors.ashby_ats_collector import AshbyATSCollector


def test_ashby_collector_normalizes_jobs(monkeypatch):
    collector = AshbyATSCollector(
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
                    "title": "Security Engineer",
                    "company": "Iota",
                    "location": "Remote",
                    "url": "https://jobs.ashbyhq.com/iota/123",
                    "description": "Security role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "ashby"
    assert jobs[0]["title"] == "Security Engineer"
