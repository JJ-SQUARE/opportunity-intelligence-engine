from pathlib import Path

from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.run_context import RunContext


def test_pipeline_orchestrator_e2e_controlled_run(tmp_path):
    outputs_path = tmp_path / "outputs"
    db_path = tmp_path / "oie_test.db"
    masters_path = tmp_path / "masters"
    cache_path = tmp_path / "http_cache"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(outputs_path)},
            "masters": {"path": str(masters_path)},
            "cache": {"base_dir": str(cache_path)},
            "sources": {
                "google_jobs": {"enabled": True},
            },
            "providers": {
                "limits": {
                    "serpapi": 5,
                    "apollo": 5,
                    "hunter": 5,
                    "openai": 5,
                },
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                    "openai": {"api_key": "fake-openai"},
                    "serpapi": {"api_key": "fake-serpapi"},
                },
            },
        },
        flags={},
    )

    orchestrator = PipelineOrchestrator(ctx)

    orchestrator.collection_service.collect = lambda: [
        {
            "title": "Backend Engineer",
            "company": "Acme Inc.",
            "location": "Remote",
            "job_url": "https://acme.com/jobs/1",
            "apply_url": "https://acme.com/apply/1",
            "description": "Python backend role",
            "source": "google_jobs",
            "detected_at": "2026-03-10",
        },
        {
            "title": "Data Engineer",
            "company": "Beta Inc.",
            "location": "Remote",
            "job_url": "https://beta.com/jobs/2",
            "apply_url": "https://beta.com/apply/2",
            "description": "Data platform role",
            "source": "linkedin_serpapi",
            "detected_at": "2026-03-10",
        },
    ]

    orchestrator.domain_resolution_service.resolve_domains = lambda companies: [
        {
            **company,
            "resolved_domain": (
                "acme.com" if "Acme" in company.get("company", "") else "beta.com"
            ),
        }
        for company in companies
    ]

    orchestrator.company_enrichment_service.enrich_companies = lambda companies: [
        {
            **company,
            "industry": "Software",
            "company_size": "51-200",
            "linkedin_url": f"https://linkedin.com/company/{company.get('company_normalized', 'company')}",
            "company_description": "Test company",
        }
        for company in companies
    ]

    orchestrator.company_classification_service.classify_companies = lambda companies: [
        {
            **company,
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.9,
            "classification_provider": "openai",
        }
        for company in companies
    ]

    orchestrator.lead_generation_service.generate_leads = lambda companies: [
        {
            "company_key": company["company_key"],
            "contact_name": f"{company['company_display']} Contact",
            "contact_title": "CTO",
            "email": f"cto@{company['resolved_domain']}",
            "linkedin_url": "https://linkedin.com/in/test",
            "lead_source": "apollo_people",
        }
        for company in companies
    ]

    result = orchestrator.run()

    assert result["status"] == "company_pipeline_completed"
    assert result["jobs_count"] == 2
    assert result["companies_count"] == 2
    assert result["leads_count"] == 2

    assert result["db_path"] is not None
    assert result["executive_summary_json"] is not None
    assert result["run_readiness_report_json"] is not None
    assert result["run_metrics_summary_json"] is not None
    assert result["run_metrics_summary"] is not None
    assert result["collector_metrics_json"] is not None
    assert result["collector_contribution_metrics_json"] is not None
    assert result["collector_roi_metrics_json"] is not None

    assert result["run_metrics_summary"]["jobs_after_dedupe"] == 2
    assert result["run_metrics_summary"]["companies_detected"] == 2

    assert Path(result["db_path"]).exists()
    assert Path(result["executive_summary_json"]).exists()
    assert Path(result["run_readiness_report_json"]).exists()
    assert Path(result["run_metrics_summary_json"]).exists()
    assert Path(result["collector_metrics_json"]).exists()
    assert Path(result["collector_contribution_metrics_json"]).exists()
    assert Path(result["collector_roi_metrics_json"]).exists()
    assert "output_dir" in ctx.paths
    assert Path(result["executive_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["run_readiness_report_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["run_metrics_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_metrics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_contribution_metrics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_roi_metrics_json"]).parent == Path(ctx.paths["output_dir"])
