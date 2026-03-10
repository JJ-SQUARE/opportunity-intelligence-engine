from oie.collectors.recruitee_ats_collector import RecruiteeATSCollector


def test_recruitee_collector_normalizes_jobs(monkeypatch):
    collector = RecruiteeATSCollector(
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
                    "title": "DevOps Engineer",
                    "company": "Kappa",
                    "location": "Remote",
                    "url": "https://kappa.recruitee.com/o/devops-engineer",
                    "description": "DevOps role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_loader)

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "recruitee"
    assert jobs[0]["title"] == "DevOps Engineer"
