from typing import Any, get_type_hints

from oie.orchestration.pipeline_stages import PIPELINE_STAGES

from oie.orchestration.run_context import (
    AccountConfig,
    DatabaseConfig,
    HubSpotDeliveryConfig,
    ProviderState,
    RunBudgets,
    RunConfig,
    RunContext,
    RunMetrics,
    RunsConfig,
    UserConfig,
)
from oie.orchestration.run_manifest import build_initial_manifest, write_manifest


def test_provider_state_contract():
    assert get_type_hints(ProviderState) == {
        "last_provider": str,
        "total_requests": int,
        "total_tokens": int,
        "total_cost_usd": float,
    }


def test_run_metrics_and_budgets_contracts():
    assert get_type_hints(RunMetrics) == {
        "total_processing_time_seconds": float,
        "total_input_count": int,
        "total_output_count": int,
        "total_rejected_count": int,
    }

    assert get_type_hints(RunBudgets) == {
        "total_cost_usd": float,
    }


def test_run_config_contract_exposes_typed_sections():
    assert set(DatabaseConfig.__annotations__) == {"path"}
    assert set(RunsConfig.__annotations__) == {"path"}
    assert get_type_hints(RunConfig) == {
        "database": DatabaseConfig,
        "runs": RunsConfig,
        "account": AccountConfig,
        "user": UserConfig,
        "hubspot_delivery": HubSpotDeliveryConfig,
        "icp_profiles": list[dict[str, Any]],
    }
    assert set(HubSpotDeliveryConfig.__annotations__) == {
        "hubspot_user_id",
        "hubspot_owner_id",
        "hubspot_company_id",
        "hubspot_credentials_ref",
    }


def test_run_context_add_provider_event_derives_status_code_from_metadata():
    ctx = RunContext.create(config={}, flags={})

    ctx.add_provider_event(
        provider="openai",
        event_type="execution_error",
        message="boom",
        metadata={"status_code": "429", "operation": "classify_company"},
    )

    assert len(ctx.provider_events) == 1
    event = ctx.provider_events[0]
    assert event["provider"] == "openai"
    assert event["event_type"] == "execution_error"
    assert event["message"] == "boom"
    assert event["status_code"] == 429
    assert event["metadata"]["operation"] == "classify_company"


def test_run_context_add_provider_event_preserves_explicit_status_code():
    ctx = RunContext.create(config={}, flags={})

    ctx.add_provider_event(
        provider="hunter",
        event_type="rate_limit",
        message="too many requests",
        metadata={"status_code": "500"},
        status_code=429,
    )

    event = ctx.provider_events[0]
    assert event["status_code"] == 429


def test_run_context_add_provider_event_handles_invalid_metadata_status_code():
    ctx = RunContext.create(config={}, flags={})

    ctx.add_provider_event(
        provider="serpapi",
        event_type="timeout",
        message="timeout",
        metadata={"status_code": "invalid"},
    )

    event = ctx.provider_events[0]
    assert event["status_code"] is None


def test_run_context_exposes_restructure_run_paths():
    ctx = RunContext.create(
        config={"runs": {"path": "tmp/runs"}, "database": {"path": "tmp/oie.db"}},
        flags={},
    )

    assert ctx.paths["db_path"] == "tmp/oie.db"
    assert ctx.paths["runs_base_dir"] == "tmp/runs"
    assert ctx.paths["run_dir"] == f"tmp/runs/{ctx.run_id}"
    assert ctx.paths["manifest_path"] == f"tmp/runs/{ctx.run_id}/manifest.json"
    assert ctx.paths["stage_dirs"]["collect_jobs"] == f"tmp/runs/{ctx.run_id}/01_collect_jobs"
    assert ctx.paths["stage_dirs"]["delivery"] == f"tmp/runs/{ctx.run_id}/10_delivery"
    assert set(ctx.paths["stage_dirs"]) == set(PIPELINE_STAGES)

def test_build_initial_manifest_uses_restructure_stages():
    ctx = RunContext.create(
        config={"runs": {"path": "tmp/runs"}},
        flags={"config_path": "config/queries.yaml"},
    )

    manifest = build_initial_manifest(ctx)

    assert manifest["run_id"] == ctx.run_id
    assert manifest["run_date"] == ctx.run_date
    assert manifest["status"] == "pending"
    assert manifest["current_stage"] is None
    assert manifest["mode"] == ctx.mode
    assert manifest["config_path"] == "config/queries.yaml"
    assert manifest["errors"] == []
    assert manifest["stages"] == {stage: "pending" for stage in PIPELINE_STAGES}

def test_write_manifest_creates_manifest_json(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={"config_path": "config/queries.yaml"},
    )
    manifest = build_initial_manifest(ctx)

    manifest_path = write_manifest(ctx, manifest)

    assert manifest_path.exists()
    assert manifest_path.as_posix() == ctx.paths["manifest_path"]
    assert '"run_id": "' + ctx.run_id + '"' in manifest_path.read_text(encoding="utf-8")

