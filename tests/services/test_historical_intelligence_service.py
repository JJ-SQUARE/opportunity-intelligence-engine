from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.historical_export_service import HistoricalExportService
from oie.services.historical_intelligence_service import HistoricalIntelligenceService
from oie.services.persistence_service import PersistenceService


def test_historical_intelligence_service_builds_history_and_growth(tmp_path):
    db_path = tmp_path / "oie_test.db"
    output_path = tmp_path / "outputs"

    ctx1 = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(output_path)},
        },
        flags={},
    )
    ctx1.run_id = "run_001"
    ctx1.run_date = "2026-03-09T00:00:00+00:00"

    persistence1 = PersistenceService(ctx1)
    persistence1.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
            }
        ],
        jobs=[
            {
                "title": "Backend Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            }
        ],
        leads=[],
    )

    ctx2 = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(output_path)},
        },
        flags={},
    )
    ctx2.run_id = "run_002"
    ctx2.run_date = "2026-03-10T00:00:00+00:00"

    persistence2 = PersistenceService(ctx2)
    persistence2.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
            }
        ],
        jobs=[
            {
                "title": "Backend Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            },
            {
                "title": "Data Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/2",
                "apply_url": "https://acme.com/apply/2",
                "description": "Data role",
                "source": "linkedin_serpapi",
                "detected_at": "2026-03-10",
            }
        ],
        leads=[],
    )

    service = HistoricalIntelligenceService(ctx2)
    export_service = HistoricalExportService(ctx2)

    history = service.build_company_hiring_history()
    growth = service.build_company_growth_summary()

    export_service.export_company_history(history)
    export_service.export_growth_summary(growth)
    export_service.export_summary_json(growth)

    assert len(history) >= 2
    assert len(growth) == 1
    assert growth[0]["company_key"] == "cmp_a"
    assert growth[0]["runs_observed"] >= 2
    assert growth[0]["openings_growth"] == 1
    assert growth[0]["trend"] == "growing"
    assert Path(ctx2.paths["historical_company_hiring_csv"]).exists()
    assert Path(ctx2.paths["historical_growth_summary_csv"]).exists()
    assert Path(ctx2.paths["historical_summary_json"]).exists()
