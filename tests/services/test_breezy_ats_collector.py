from oie.collectors.breezy_ats_collector import BreezyATSCollector


def test_breezy_collector_normalizes_jobs(monkeypatch):
    collector = BreezyATSCollector(
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
                    "title": "QA Engineer",
                    "company": "Lambda",
                    "location": "Remote",
                    "url": "https://lambda.breezy.hr/p/123",
                    "description": "QA role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "breezy"
    assert jobs[0]["title"] == "QA Engineer"
