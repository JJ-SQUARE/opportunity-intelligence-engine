from __future__ import annotations

from oie.orchestration.run_context import RunContext
from oie.services.master_data_service import MasterDataService


def test_master_data_service_appends_jobs_with_run_metadata(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    count = service.append_jobs(
        [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            }
        ]
    )

    rows = service.read_master_rows("jobs")

    assert count == 1
    assert rows[0]["title"] == "Backend Engineer"
    assert rows[0]["run_id"] == ctx.run_id


def test_master_data_service_appends_companies_with_ai_identity_fields(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    count = service.append_companies(
        [
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "company_root": "acme",
                "ai_company_identity_confidence": 0.91,
                "ai_company_identity_source": "job_intelligence",
                "ai_company_identity_reason": "AI validated hiring company.",
                "company_identity_ai_valid": True,
                "company_identity_ai_contaminated": False,
                "company_identity_ai_ambiguous": False,
                "enrichment_ai_match": True,
                "enrichment_ai_confidence": 0.93,
                "enrichment_ai_decision": "accepted",
                "enrichment_ai_reason": "Apollo data matches Acme.",
                "enrichment_ai_provider": "openai",
                "enrichment_ai_model": "gpt-4.1-mini",
                "enrichment_ai_mode": "live_api",
            }
        ]
    )

    rows = service.read_master_rows("companies")

    assert count == 1
    assert rows[0]["company_key"] == "cmp_a"
    assert rows[0]["ai_company_identity_confidence"] == "0.91"
    assert rows[0]["ai_company_identity_source"] == "job_intelligence"
    assert rows[0]["company_identity_ai_valid"] == "True"
    assert rows[0]["company_identity_ai_contaminated"] == "False"
    assert rows[0]["company_identity_ai_ambiguous"] == "False"
    assert rows[0]["enrichment_ai_match"] == "True"
    assert rows[0]["enrichment_ai_confidence"] == "0.93"
    assert rows[0]["enrichment_ai_decision"] == "accepted"
    assert rows[0]["enrichment_ai_provider"] == "openai"
    assert rows[0]["run_id"] == ctx.run_id


def test_master_data_service_skips_write_on_schema_mismatch(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    service.append_entity_rows(
        "jobs",
        [{"foo": "bar"}],
        ["foo"],
    )

    count = service.safe_append_entity_rows(
        "jobs",
        [{"title": "Backend Engineer"}],
        ["title", "run_id", "run_date"],
    )

    assert count == 0
    assert ctx.metrics["master_jobs_write_skipped_schema_error"] is True


def test_master_data_service_appends_leads_with_scored_fields(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    count = service.append_leads(
        [
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
                "email_quality_score": 95,
                "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
                "lead_relevance_score": 197,
                "target_persona": "Technology Leadership",
                "suggested_titles": "CTO, VP Engineering",
                "search_reason": "Owns engineering staffing and delivery decisions.",
                "pain_alignment": "Strategic engineering hiring need.",
                "priority": "high",
                "recommended_channel": "email",
                "lead_role_type": "primary_decision_maker",
                "why_selected": "Owns technical staffing decisions.",
                "outreach_angle": "Discuss senior engineering capacity.",
                "expected_relevance": "high",
                "risk_or_uncertainty": "Role scope may be broader than engineering.",
            }
        ]
    )

    rows = service.read_master_rows("leads")

    assert count == 1
    assert rows[0]["company_key"] == "cmp_a"
    assert rows[0]["email"] == "jane@acme.com"
    assert rows[0]["email_quality_score"] == "95"
    assert rows[0]["lead_capture_reason"] == "apollo_match | title:CTO | email_quality:95"
    assert rows[0]["lead_relevance_score"] == "197"
    assert rows[0]["target_persona"] == "Technology Leadership"
    assert rows[0]["suggested_titles"] == "CTO, VP Engineering"
    assert rows[0]["search_reason"] == "Owns engineering staffing and delivery decisions."
    assert rows[0]["pain_alignment"] == "Strategic engineering hiring need."
    assert rows[0]["priority"] == "high"
    assert rows[0]["recommended_channel"] == "email"
    assert rows[0]["lead_role_type"] == "primary_decision_maker"
    assert rows[0]["why_selected"] == "Owns technical staffing decisions."
    assert rows[0]["outreach_angle"] == "Discuss senior engineering capacity."
    assert rows[0]["expected_relevance"] == "high"
    assert rows[0]["risk_or_uncertainty"] == "Role scope may be broader than engineering."
    assert rows[0]["run_id"] == ctx.run_id


def test_master_data_service_accumulates_schema_error_metrics(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    service.append_entity_rows(
        "jobs",
        [{"foo": "bar"}],
        ["foo"],
    )

    count = service.safe_append_entity_rows(
        "jobs",
        [{"title": "Backend Engineer"}],
        ["title", "run_id", "run_date"],
    )

    assert count == 0
    assert ctx.metrics["master_jobs_write_skipped_schema_error"] is True
    assert ctx.metrics["master_jobs_write_succeeded"] is False
    assert ctx.metrics["master_jobs_write_attempted"] == 1
    assert ctx.metrics["master_schema_errors_count"] == 1

def test_master_data_service_migrates_additive_schema_and_tracks_metrics(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    service.append_entity_rows(
        "jobs",
        [{"foo": "bar"}],
        ["foo"],
    )

    count = service.append_entity_rows(
        "jobs",
        [{"foo": "bar", "title": "Backend Engineer"}],
        ["foo", "title"],
    )

    rows = service.read_master_rows("jobs")

    assert count == 1
    assert rows[0]["foo"] == "bar"
    assert rows[0]["title"] == ""
    assert rows[1]["title"] == "Backend Engineer"
    assert ctx.metrics["master_jobs_schema_migrated"] is True
    assert ctx.metrics["master_jobs_schema_columns_added"] == 1
    assert ctx.metrics["master_jobs_schema_migrations_count"] == 1


def test_master_data_service_safe_append_tracks_generic_write_errors(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    original_append_rows = service._append_rows

    def boom(path, fieldnames, rows):
        raise OSError("disk full")

    service._append_rows = boom
    try:
        count = service.safe_append_entity_rows(
            "jobs",
            [{"title": "Backend Engineer"}],
            ["title"],
        )
    finally:
        service._append_rows = original_append_rows

    assert count == 0
    assert ctx.metrics["master_jobs_write_failed_error"] is True
    assert ctx.metrics["master_jobs_write_succeeded"] is False
    assert ctx.metrics["master_jobs_write_attempted"] == 1
    assert ctx.metrics["master_jobs_write_errors_count"] == 1
    assert len(ctx.provider_events) == 1
    assert ctx.provider_events[0]["provider"] == "master_data"
    assert ctx.provider_events[0]["event_type"] == "write_error"

