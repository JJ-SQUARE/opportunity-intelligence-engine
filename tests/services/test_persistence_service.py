from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.persistence.sqlite import get_connection
from oie.services.persistence_service import PersistenceService


def test_persistence_service_persist_run_snapshot_writes_core_records(tmp_path):
    db_path = tmp_path / "oie_test.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_after_dedupe"] = 2
    ctx.provider_state["company_merge_candidates"] = [
        {
            "company_key_left": "cmp_a",
            "company_key_right": "cmp_b",
            "reason": "same_company_root",
            "confidence": 0.8,
        }
    ]
    ctx.add_provider_event(
        provider="openai",
        event_type="execution_error",
        message="boom",
        metadata={"status_code": 500},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.9,
                "domain_candidate": "acme.com",
                "domain_validation_status": "accepted",
                "domain_review_required": 0,
                "domain_ai_validated": 1,
                "domain_ai_decision": "accepted",
                "domain_ai_confidence": 0.91,
                "domain_ai_reason": "brand_match",
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
                "opportunity_score": 42,
                "score_openings": 16,
                "score_remote": 8,
                "score_contractor": 6,
                "score_multi_source": 10,
                "score_company_type": 2,
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
                "detected_at": "2026-03-10",
            }
        ],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
            }
        ],
    )

    assert Path(db_path).exists()

    conn = get_connection(str(db_path))
    try:
        run_row = conn.execute(
            "SELECT run_id, status FROM runs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchone()
        assert run_row is not None
        assert run_row["status"] == "ok"

        metric_row = conn.execute(
            "SELECT metric_value FROM run_metrics WHERE run_id = ? AND metric_key = ?",
            (ctx.run_id, "jobs_after_dedupe"),
        ).fetchone()
        assert metric_row is not None
        assert metric_row["metric_value"] == "2"

        events = conn.execute(
            "SELECT provider, event_type, status_code FROM provider_events WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(events) == 1
        assert events[0]["provider"] == "openai"

        companies = conn.execute(
            """
            SELECT
                company_key,
                resolved_domain,
                domain_candidate,
                domain_validation_status,
                domain_ai_decision
            FROM companies
            """
        ).fetchall()
        assert len(companies) == 1
        assert companies[0]["company_key"] == "cmp_a"
        assert companies[0]["resolved_domain"] == "acme.com"
        assert companies[0]["domain_candidate"] == "acme.com"
        assert companies[0]["domain_validation_status"] == "accepted"
        assert companies[0]["domain_ai_decision"] == "accepted"

        aliases = conn.execute(
            "SELECT company_key, alias_value, alias_normalized, alias_type FROM company_aliases"
        ).fetchall()
        assert len(aliases) == 1
        assert aliases[0]["company_key"] == "cmp_a"
        assert aliases[0]["alias_value"] == "Acme Inc."
        assert aliases[0]["alias_normalized"] == "acme"
        assert aliases[0]["alias_type"] == "observed_name"

        domains = conn.execute(
            "SELECT company_key, domain, source, confidence, is_primary FROM domains"
        ).fetchall()
        assert len(domains) == 1
        assert domains[0]["company_key"] == "cmp_a"
        assert domains[0]["domain"] == "acme.com"
        assert domains[0]["source"] == "apply_url"
        assert domains[0]["confidence"] == 0.9
        assert domains[0]["is_primary"] == 1

        merge_candidates = conn.execute(
            "SELECT run_id, company_key_left, company_key_right, reason, confidence FROM company_merge_candidates WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(merge_candidates) == 1
        assert merge_candidates[0]["company_key_left"] == "cmp_a"
        assert merge_candidates[0]["company_key_right"] == "cmp_b"
        assert merge_candidates[0]["reason"] == "same_company_root"
        assert merge_candidates[0]["confidence"] == 0.8

        company_scores = conn.execute(
            """
            SELECT
                run_id,
                company_key,
                opportunity_score,
                score_openings,
                score_remote,
                score_contractor,
                score_multi_source,
                score_company_type
            FROM company_scores
            WHERE run_id = ?
            """,
            (ctx.run_id,),
        ).fetchall()
        assert len(company_scores) == 1
        assert company_scores[0]["company_key"] == "cmp_a"
        assert company_scores[0]["opportunity_score"] == 42
        assert company_scores[0]["score_openings"] == 16
        assert company_scores[0]["score_remote"] == 8
        assert company_scores[0]["score_contractor"] == 6
        assert company_scores[0]["score_multi_source"] == 10
        assert company_scores[0]["score_company_type"] == 2

        jobs = conn.execute(
            "SELECT company_key FROM jobs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(jobs) == 1
        assert jobs[0]["company_key"] == "cmp_a"

        leads = conn.execute(
            "SELECT email FROM leads WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(leads) == 1
        assert leads[0]["email"] == "jane@acme.com"
    finally:
        conn.close()


def test_persistence_service_persist_run_snapshot_allows_optional_entities(tmp_path):
    db_path = tmp_path / "oie_test_optional.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="partial")

    conn = get_connection(str(db_path))
    try:
        run_row = conn.execute(
            "SELECT run_id, status FROM runs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchone()

        assert run_row is not None
        assert run_row["status"] == "partial"
    finally:
        conn.close()


def test_persistence_service_persist_run_snapshot_writes_scored_lead_fields(tmp_path):
    db_path = tmp_path / "oie_test_scored_leads.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(
        status="ok",
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "Jane@Acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
                "lead_source": "apollo_people",
                "lead_confidence": 0.9,
                "email_quality_score": 95,
                "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
                "lead_relevance_score": 197,
            }
        ],
    )

    conn = get_connection(str(db_path))
    try:
        lead = conn.execute(
            """
            SELECT
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_confidence,
                email_quality_score,
                lead_capture_reason,
                lead_relevance_score
            FROM leads
            WHERE run_id = ?
            """,
            (ctx.run_id,),
        ).fetchone()

        assert lead is not None
        assert lead["company_key"] == "cmp_a"
        assert lead["contact_name"] == "Jane Doe"
        assert lead["contact_title"] == "CTO"
        assert lead["email"] == "jane@acme.com"
        assert lead["linkedin_url"] == "https://linkedin.com/in/jane"
        assert lead["lead_source"] == "apollo_people"
        assert lead["lead_confidence"] == 0.9
        assert lead["email_quality_score"] == 95
        assert lead["lead_capture_reason"] == "apollo_match | title:CTO | email_quality:95"
        assert lead["lead_relevance_score"] == 197
    finally:
        conn.close()


def test_persistence_service_persist_run_snapshot_normalizes_lead_fields(tmp_path):
    db_path = tmp_path / "oie_test_normalized_leads.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(
        status="ok",
        leads=[
            {
                "company_key": "  cmp_a  ",
                "contact_name": "  Jane Doe  ",
                "contact_title": "  CTO  ",
                "email": "  Jane.Doe@Acme.com  ",
                "linkedin_url": "  https://linkedin.com/in/jane  ",
                "lead_source": "  apollo_people  ",
                "lead_confidence": 0.9,
                "email_quality_score": 95,
                "lead_capture_reason": "  apollo_match | title:CTO | email_quality:95  ",
                "lead_relevance_score": 197,
            }
        ],
    )

    conn = get_connection(str(db_path))
    try:
        lead = conn.execute(
            """
            SELECT
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_capture_reason
            FROM leads
            WHERE run_id = ?
            """,
            (ctx.run_id,),
        ).fetchone()

        assert lead is not None
        assert lead["company_key"] == "cmp_a"
        assert lead["contact_name"] == "Jane Doe"
        assert lead["contact_title"] == "CTO"
        assert lead["email"] == "jane.doe@acme.com"
        assert lead["linkedin_url"] == "https://linkedin.com/in/jane"
        assert lead["lead_source"] == "apollo_people"
        assert lead["lead_capture_reason"] == "apollo_match | title:CTO | email_quality:95"
    finally:
        conn.close()
