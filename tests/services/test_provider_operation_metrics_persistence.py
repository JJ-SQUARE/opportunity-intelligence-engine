from oie.orchestration.run_context import RunContext
from oie.services.persistence_service import PersistenceService
from oie.persistence.sqlite import get_connection


def test_persistence_service_writes_provider_operation_metrics(tmp_path):
    db_path = tmp_path / "oie_test.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )

    ctx.metrics.update(
        {
            "serpapi_search_google_max_calls": 25,
            "serpapi_search_google_used_calls": 10,
            "serpapi_search_google_remaining_calls": 15,
            "serpapi_search_google_started": 10,
            "serpapi_search_google_success": 9,
            "serpapi_search_google_retry_count": 1,
            "openai_classify_company_max_calls": 80,
            "openai_classify_company_used_calls": 20,
            "openai_classify_company_remaining_calls": 60,
            "openai_classify_company_started": 20,
            "openai_classify_company_success": 18,
            "openai_classify_company_blocked_budget": 4,
            "openai_classify_company_errors_execution_error": 2,
        }
    )

    service = PersistenceService(ctx)
    service.persist_run_snapshot(status="ok", companies=[], jobs=[], leads=[])

    conn = get_connection(str(db_path))
    try:
        rows = conn.execute(
            """
            SELECT
                provider,
                operation,
                max_calls,
                used_calls,
                remaining_calls,
                started,
                success,
                retry_count,
                blocked_budget,
                errors_timeout,
                errors_execution_error
            FROM provider_operation_metrics
            WHERE run_id = ?
            ORDER BY provider, operation
            """,
            (ctx.run_id,),
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 2

    serp_row = dict(rows[0])
    openai_row = dict(rows[1])

    assert serp_row["provider"] == "openai" or serp_row["provider"] == "serpapi"
    assert openai_row["provider"] == "openai" or openai_row["provider"] == "serpapi"

    serp = next(r for r in map(dict, rows) if r["provider"] == "serpapi")
    openai = next(r for r in map(dict, rows) if r["provider"] == "openai")

    assert serp["operation"] == "search_google"
    assert serp["max_calls"] == 25
    assert serp["used_calls"] == 10
    assert serp["remaining_calls"] == 15
    assert serp["started"] == 10
    assert serp["success"] == 9
    assert serp["retry_count"] == 1
    assert serp["blocked_budget"] == 0
    assert serp["errors_timeout"] == 0
    assert serp["errors_execution_error"] == 0

    assert openai["operation"] == "classify_company"
    assert openai["max_calls"] == 80
    assert openai["used_calls"] == 20
    assert openai["remaining_calls"] == 60
    assert openai["started"] == 20
    assert openai["success"] == 18
    assert openai["retry_count"] == 0
    assert openai["blocked_budget"] == 4
    assert openai["errors_timeout"] == 0
    assert openai["errors_execution_error"] == 2
