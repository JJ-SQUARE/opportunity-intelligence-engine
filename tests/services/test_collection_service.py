from oie.orchestration.run_context import RunContext
from oie.services.collection_service import CollectionService


def test_collection_service_collects_from_enabled_google_jobs(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {
                "google_jobs": {
                    "enabled": True,
                    "location_mode": "matrix",
                    "locations": ["Ecuador"],
                }
            },
            "queries": [{"name": "SE", "q": "desarrollador remoto"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "google_jobs")

    def fake_load_legacy():
        def fake_collect(payload):
            assert payload["run"]["num_pages"] == 3
            assert payload["source_config"]["locations"] == ["Ecuador"]
            assert payload["queries"][0]["q"] == "desarrollador remoto"
            return [
                {
                    "title": "Python Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "job_url": "https://example.com/job/1",
                    "apply_url": "https://example.com/apply/1",
                    "description": "Python role",
                    "detected_at": "2026-03-09",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "google_jobs"
    assert jobs[0]["title"] == "Python Engineer"
    assert ctx.metrics["jobs_collected_raw"] == 1


def test_collection_service_collects_from_enabled_indeed(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {
                "discovery": {
                    "indeed_serpapi": {
                        "enabled": True,
                        "num_pages": 5,
                        "sleep_s": 1.0,
                    }
                }
            },
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "indeed_serpapi")

    def fake_load_legacy():
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

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "indeed_serpapi"
    assert jobs[0]["title"] == "Data Analyst"


def test_collection_service_collects_from_enabled_career_pages(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {
                "discovery": {
                    "career_pages_serpapi": {
                        "enabled": True,
                        "num_pages": 5,
                        "sleep_s": 1.0,
                    }
                }
            },
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "career_pages_serpapi")

    def fake_load_legacy():
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

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "career_pages_serpapi"
    assert jobs[0]["title"] == "Machine Learning Engineer"


def test_collection_service_collects_from_enabled_greenhouse(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {"ats": {"greenhouse": {"enabled": True}}},
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "greenhouse")

    def fake_load_legacy():
        def fake_collect(**kwargs):
            return [
                {
                    "title": "Data Platform Engineer",
                    "company": "Beta",
                    "location": "Remote",
                    "url": "https://boards.greenhouse.io/beta/jobs/1",
                    "description": "Data infra",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "greenhouse"
    assert jobs[0]["title"] == "Data Platform Engineer"


def test_collection_service_collects_from_enabled_lever(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {"ats": {"lever": {"enabled": True}}},
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "lever")

    def fake_load_legacy():
        def fake_collect(**kwargs):
            return [
                {
                    "title": "Site Reliability Engineer",
                    "company": "Delta",
                    "location": "Remote",
                    "url": "https://jobs.lever.co/delta/1",
                    "description": "Infra role",
                }
            ]
        return fake_collect

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "lever"
    assert jobs[0]["title"] == "Site Reliability Engineer"


def test_collection_service_collects_from_enabled_workable(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {"ats": {"workable": {"enabled": True}}},
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "workable")

    def fake_load_legacy():
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

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "workable"
    assert jobs[0]["title"] == "Backend Developer"


def test_collection_service_collects_from_enabled_teamtailor(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {"ats": {"teamtailor": {"enabled": True}}},
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "teamtailor")

    def fake_load_legacy():
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

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "teamtailor"
    assert jobs[0]["title"] == "Full Stack Engineer"


def test_collection_service_collects_from_enabled_breezy(monkeypatch):
    ctx = RunContext.create(
        config={
            "run": {"num_pages": 3, "sleep_s": 1.0},
            "sources": {"ats": {"breezy": {"enabled": True}}},
            "queries": [{"name": "SE", "q": "python developer"}],
        },
        flags={},
    )

    service = CollectionService(ctx)
    service._build_collectors()

    collector = next(c for c in service.collector_runner.registry.all() if c.collector_name == "breezy")

    def fake_load_legacy():
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

    monkeypatch.setattr(collector, "_load_legacy_collector", fake_load_legacy)
    jobs = service.collect()

    assert len(jobs) == 1
    assert jobs[0]["source"] == "breezy"
    assert jobs[0]["title"] == "QA Engineer"
