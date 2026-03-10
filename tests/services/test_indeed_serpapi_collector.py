from oie.collectors.indeed_serpapi_collector import IndeedSerpAPICollector


def test_indeed_collector_normalizes_jobs(monkeypatch):
    collector = IndeedSerpAPICollector(
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
                    "title": "Data Analyst",
                    "company": "Zeta",
                    "location": "Remote",
                    "url": "https://indeed.com/viewjob?jk=123",
                    "description": "Analytics role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "indeed_serpapi"
    assert jobs[0]["title"] == "Data Analyst"
