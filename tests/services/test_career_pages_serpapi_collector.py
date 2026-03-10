from oie.collectors.career_pages_serpapi_collector import CareerPagesSerpAPICollector


def test_career_pages_collector_normalizes_jobs(monkeypatch):
    collector = CareerPagesSerpAPICollector(
        config={
            "queries": [{"q": "python developer"}],
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "source_config": {"enabled": True, "num_pages": 5, "sleep_s": 1.0},
        }
    )

    def fake_loader():
        def fake_collect(**kwargs):
            return [
                {
                    "title": "Machine Learning Engineer",
                    "company": "Eta",
                    "location": "Remote",
                    "url": "https://careers.eta.com/jobs/123",
                    "description": "ML role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "career_pages_serpapi"
    assert jobs[0]["title"] == "Machine Learning Engineer"
