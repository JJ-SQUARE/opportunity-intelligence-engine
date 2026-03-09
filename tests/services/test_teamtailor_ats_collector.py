from oie.collectors.teamtailor_ats_collector import TeamtailorATSCollector


def test_teamtailor_collector_normalizes_jobs(monkeypatch):
    collector = TeamtailorATSCollector(
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
                    "title": "Full Stack Engineer",
                    "company": "Sigma",
                    "location": "Remote",
                    "url": "https://sigma.teamtailor.com/jobs/123",
                    "description": "Full stack role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "teamtailor"
    assert jobs[0]["title"] == "Full Stack Engineer"
