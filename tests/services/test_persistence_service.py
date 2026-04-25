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
                "enrichment_ai_match": True,
                "enrichment_ai_confidence": 0.93,
                "enrichment_ai_decision": "accepted",
                "enrichment_ai_reason": "Apollo data matches Acme.",
                "enrichment_ai_provider": "openai",
                "enrichment_ai_model": "gpt-4.1-mini",
                "enrichment_ai_mode": "live_api",
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
                domain_ai_decision,
                enrichment_ai_match,
                enrichment_ai_confidence,
                enrichment_ai_decision
            FROM companies
            """
        ).fetchall()
        assert len(companies) == 1
        assert companies[0]["company_key"] == "cmp_a"
        assert companies[0]["resolved_domain"] == "acme.com"
        assert companies[0]["domain_candidate"] == "acme.com"
        assert companies[0]["domain_validation_status"] == "accepted"
        assert companies[0]["domain_ai_decision"] == "accepted"
        assert companies[0]["enrichment_ai_match"] == 1
        assert companies[0]["enrichment_ai_confidence"] == 0.93
        assert companies[0]["enrichment_ai_decision"] == "accepted"

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
                lead_relevance_score,
                target_persona,
                suggested_titles,
                search_reason,
                pain_alignment,
                priority,
                recommended_channel,
                lead_role_type,
                why_selected,
                outreach_angle,
                expected_relevance,
                risk_or_uncertainty
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
        assert lead["target_persona"] == "Technology Leadership"
        assert lead["suggested_titles"] == "CTO, VP Engineering"
        assert lead["search_reason"] == "Owns engineering staffing and delivery decisions."
        assert lead["pain_alignment"] == "Strategic engineering hiring need."
        assert lead["priority"] == "high"
        assert lead["recommended_channel"] == "email"
        assert lead["lead_role_type"] == "primary_decision_maker"
        assert lead["why_selected"] == "Owns technical staffing decisions."
        assert lead["outreach_angle"] == "Discuss senior engineering capacity."
        assert lead["expected_relevance"] == "high"
        assert lead["risk_or_uncertainty"] == "Role scope may be broader than engineering."
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

def test_persistence_service_persist_run_snapshot_survives_partial_company_failure(tmp_path):
    db_path = tmp_path / "oie_test_partial_failure.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_after_dedupe"] = 3

    service = PersistenceService(ctx)

    original_persist_companies = service.persist_companies

    def boom(companies):
        raise RuntimeError("companies write failed")

    service.persist_companies = boom
    try:
        service.persist_run_snapshot(
            status="partial_ok",
            companies=[
                {
                    "company_key": "cmp_a",
                    "company_display": "Acme Inc.",
                    "company_normalized": "acme",
                    "resolved_domain": "acme.com",
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
    finally:
        service.persist_companies = original_persist_companies

    conn = get_connection(str(db_path))
    try:
        run_row = conn.execute(
            "SELECT run_id, status FROM runs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchone()
        assert run_row is not None
        assert run_row["status"] == "partial_ok"

        metric_row = conn.execute(
            "SELECT metric_value FROM run_metrics WHERE run_id = ? AND metric_key = ?",
            (ctx.run_id, "jobs_after_dedupe"),
        ).fetchone()
        assert metric_row is not None
        assert metric_row["metric_value"] == "3"

        jobs = conn.execute(
            "SELECT title FROM jobs WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(jobs) == 1

        leads = conn.execute(
            "SELECT email FROM leads WHERE run_id = ?",
            (ctx.run_id,),
        ).fetchall()
        assert len(leads) == 1
        assert leads[0]["email"] == "jane@acme.com"

        companies = conn.execute(
            "SELECT company_key FROM companies WHERE company_key = ?",
            ("cmp_a",),
        ).fetchall()
        assert len(companies) == 0
    finally:
        conn.close()

    assert ctx.metrics["persistence_companies_succeeded"] is False
    assert ctx.metrics["persistence_jobs_succeeded"] is True
    assert ctx.metrics["persistence_leads_succeeded"] is True
    assert ctx.metrics["persistence_errors_count"] >= 1
    assert any(
        event["provider"] == "persistence" and event["event_type"] == "persist_error"
        for event in ctx.provider_events
    )

