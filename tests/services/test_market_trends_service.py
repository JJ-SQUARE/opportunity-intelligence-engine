from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.market_trends_export_service import MarketTrendsExportService
from oie.services.market_trends_service import MarketTrendsService
from oie.services.persistence_service import PersistenceService


def test_market_trends_service_builds_and_exports_aggregates(tmp_path):
    db_path = tmp_path / "oie_test.db"
    output_path = tmp_path / "outputs"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(output_path)},
        },
        flags={},
    )
    ctx.run_id = "run_001"
    ctx.run_date = "2026-03-10T00:00:00+00:00"

    persistence = PersistenceService(ctx)
    persistence.persist_run_snapshot(
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
            },
            {
                "company_key": "cmp_b",
                "company_display": "Beta Inc.",
                "company_normalized": "beta",
                "resolved_domain": "beta.com",
                "aliases": ["Beta Inc."],
                "alias_type_map": {
                    "Beta Inc.": "beta",
                    "Beta Inc.__type": "observed_name",
                },
            },
        ],
        jobs=[
            {
                "title": "Backend Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Ecuador",
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
                "location": "Ecuador",
                "job_url": "https://acme.com/jobs/2",
                "apply_url": "https://acme.com/apply/2",
                "description": "Data role",
                "source": "linkedin_serpapi",
                "detected_at": "2026-03-10",
            },
            {
                "title": "Frontend Engineer",
                "company": "Beta Inc.",
                "company_key": "cmp_b",
                "location": "Mexico",
                "job_url": "https://beta.com/jobs/1",
                "apply_url": "https://beta.com/apply/1",
                "description": "Frontend role",
                "source": "google_jobs",
                "detected_at": "2026-03-10",
            },
        ],
        leads=[],
    )

    service = MarketTrendsService(ctx)
    export_service = MarketTrendsExportService(ctx)

    source_rows = service.build_source_trends()
    country_rows = service.build_country_trends()
    new_company_rows = service.build_new_companies_by_source()
    summary = service.build_summary()

    export_service.export_source_trends(source_rows)
    export_service.export_country_trends(country_rows)
    export_service.export_new_companies_by_source(new_company_rows)
    export_service.export_summary_json(summary)

    assert len(source_rows) >= 2
    assert len(country_rows) >= 2
    assert len(new_company_rows) >= 1
    assert "top_sources" in summary
    assert Path(ctx.paths["market_trends_by_source_csv"]).exists()
    assert Path(ctx.paths["market_trends_by_location_csv"]).exists()
    assert Path(ctx.paths["market_new_companies_by_source_csv"]).exists()
    assert Path(ctx.paths["market_trends_summary_json"]).exists()
