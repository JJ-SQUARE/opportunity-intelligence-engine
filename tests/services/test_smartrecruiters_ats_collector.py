from oie.collectors.smartrecruiters_ats_collector import SmartRecruitersATSCollector


def test_smartrecruiters_collector_normalizes_jobs(monkeypatch):
    collector = SmartRecruitersATSCollector(
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
                    "company": "Theta",
                    "location": "Remote",
                    "url": "https://jobs.smartrecruiters.com/Theta/123",
                    "description": "Platform role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "smartrecruiters"
    assert jobs[0]["title"] == "Platform Engineer"
