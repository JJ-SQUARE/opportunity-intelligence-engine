from oie.collectors.linkedin_serpapi_collector import LinkedInSerpAPICollector


def test_linkedin_collector_normalizes_jobs(monkeypatch):

    collector = LinkedInSerpAPICollector(
        config={
            "queries": [{"q": "python developer"}],
            "run": {"num_pages": 3},
            "source_config": {"enabled": True},
        }
    )

    def fake_loader():

        def fake_collect(**kwargs):
            return [
                {
                    "title": "Python Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://linkedin/job/1",
                }
            ]

        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "linkedin_serpapi"
    assert jobs[0]["title"] == "Python Engineer"
