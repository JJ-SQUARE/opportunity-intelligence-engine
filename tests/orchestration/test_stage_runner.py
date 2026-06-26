import json
from typing import Any, get_type_hints

from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_artifacts import StageArtifactPaths
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint import REQUIRED_CHECKPOINT_FIELDS, load_checkpoint_payload
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_errors import ErrorRecord, build_error_record
from oie.orchestration.stage_costs import CostEstimate
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_metrics import StageMetrics
from oie.orchestration.stage_provider_usage import ProviderUsage
from oie.orchestration.stage_result import StageResult
from oie.orchestration.stage_runner import StageRunner
from oie.orchestration.stage_state import StageState


def test_build_error_record_returns_exception_type_and_message():
    error = build_error_record(RuntimeError("controlled failure"))

    assert error == {
        "error_type": "RuntimeError",
        "error_message": "controlled failure",
    }


def test_error_record_contract():
    assert get_type_hints(ErrorRecord) == {
        "error_type": str,
        "error_message": str,
    }


def test_stage_artifact_paths_contract():
    assert get_type_hints(StageArtifactPaths) == {
        "stage_dir": Path,
        "output": Path,
        "checkpoint": Path,
        "metrics": Path,
    }


def test_stage_item_contract():
    assert get_type_hints(StageItem) == {
        "id": str,
        "value": object,
        "metadata": dict[str, Any],
    }


def test_stage_item_jsonl_round_trip(tmp_path):
    from oie.orchestration.stage_io import append_jsonl_item, read_jsonl_file

    path = tmp_path / "items.jsonl"
    item: StageItem = {"id": "item_1", "value": 10, "metadata": {"source": "test"}}

    append_jsonl_item(path, item)

    assert read_jsonl_file(path) == [item]


def test_provider_usage_and_cost_estimate_contracts():
    assert ProviderUsage == dict[str, Any]
    assert CostEstimate == dict[str, Any]


def test_stage_metrics_contract():
    assert get_type_hints(StageMetrics) == {
        "run_id": str,
        "stage": str,
        "status": str,
        "input_count": int,
        "processed_count": int,
        "output_count": int,
        "rejected_count": int,
        "error_count": int,
        "provider_usage": dict[str, Any],
        "cost_estimate": dict[str, Any],
        "processing_time_seconds": float,
    }


def test_stage_result_contract():
    assert get_type_hints(StageResult) == {
        "run_id": str,
        "stage": str,
        "status": str,
        "checkpoint": StageState,
        "metrics": StageMetrics,
    }


def test_required_checkpoint_fields_follow_stage_state_contract():
    assert REQUIRED_CHECKPOINT_FIELDS == set(get_type_hints(StageState))


def test_load_checkpoint_payload_rejects_non_object_payload():
    try:
        load_checkpoint_payload(["not", "a", "dict"])
    except TypeError as exc:
        assert str(exc) == "Checkpoint payload must be a JSON object."
    else:
        raise AssertionError("Expected TypeError")


def test_load_checkpoint_payload_rejects_invalid_field_type():
    checkpoint = {
        "run_id": 123,
        "stage": "collect_jobs",
        "status": "running",
        "input_count": 0,
        "processed_count": 0,
        "output_count": 0,
        "rejected_count": 0,
        "last_processed_index": None,
        "last_processed_id": None,
        "errors": [],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.0,
    }

    try:
        load_checkpoint_payload(checkpoint)
    except TypeError as exc:
        assert str(exc) == "Checkpoint field has invalid type: run_id"
    else:
        raise AssertionError("Expected TypeError")


def test_load_checkpoint_payload_rejects_invalid_nullable_field_type():
    checkpoint = {
        "run_id": "run_1",
        "stage": "collect_jobs",
        "status": "running",
        "input_count": 0,
        "processed_count": 0,
        "output_count": 0,
        "rejected_count": 0,
        "last_processed_index": "0",
        "last_processed_id": None,
        "errors": [],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.0,
    }

    try:
        load_checkpoint_payload(checkpoint)
    except TypeError as exc:
        assert str(exc) == "Checkpoint field has invalid type: last_processed_index"
    else:
        raise AssertionError("Expected TypeError")


def test_load_checkpoint_payload_rejects_missing_required_fields():
    try:
        load_checkpoint_payload({"run_id": "run_1"})
    except ValueError as exc:
        assert "Checkpoint payload missing required fields:" in str(exc)
        assert "stage" in str(exc)
        assert "status" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


class RunnerDummyStage(Stage):
    name = "collect_jobs"
    order = 1


class RunnerItemsStage(Stage):
    name = "company_gate"
    order = 2

    def load_input(self):
        return [
            {"id": "item_1", "value": 1},
            {"id": "item_2", "value": 2},
        ]

    def process_item(self, item):
        return {
            "id": item["id"],
            "value": item["value"] * 10,
        }


class RunnerFailingStage(Stage):
    name = "freshness_gate"
    order = 3

    def load_input(self):
        return [
            {"id": "ok_1", "value": 1},
            {"id": "boom", "value": 2},
        ]

    def process_item(self, item):
        if item["id"] == "boom":
            raise RuntimeError("controlled stage failure")
        return {
            "id": item["id"],
            "value": item["value"] * 10,
        }


class RunnerRecoveredStage(Stage):
    name = "freshness_gate"
    order = 3

    def load_input(self):
        return [
            {"id": "ok_1", "value": 1},
            {"id": "boom", "value": 2},
        ]

    def process_item(self, item):
        return {
            "id": item["id"],
            "value": item["value"] * 10,
        }


class RunnerImmediatelyFailingStage(Stage):
    name = "domain_gate"
    order = 4

    def load_input(self):
        return [
            {"id": "boom", "value": 1},
        ]

    def process_item(self, item):
        raise RuntimeError("immediate failure")


def test_stage_runner_writes_initial_checkpoint(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    checkpoint = StageRunner(ctx).run_stage(RunnerDummyStage)
    checkpoint_path = RunnerDummyStage(ctx).artifact_paths()["checkpoint"]
    saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    assert checkpoint["run_id"] == ctx.run_id
    assert checkpoint["stage"] == "collect_jobs"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 0
    assert checkpoint["processed_count"] == 0
    assert checkpoint["output_count"] == 0
    assert saved == checkpoint

def test_stage_runner_persists_output_jsonl_and_updates_checkpoint(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    checkpoint = StageRunner(ctx).run_stage(RunnerItemsStage)
    paths = RunnerItemsStage(ctx).artifact_paths()

    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()
    saved_checkpoint = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))

    assert [json.loads(line) for line in output_lines] == [
        {"id": "item_1", "value": 10},
        {"id": "item_2", "value": 20},
    ]
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 2
    assert checkpoint["processed_count"] == 2
    assert checkpoint["output_count"] == 2
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))

    assert checkpoint["last_processed_index"] == 1
    assert checkpoint["last_processed_id"] == "item_2"
    assert saved_checkpoint == checkpoint
    assert metrics["status"] == "completed"
    assert metrics["input_count"] == 2
    assert metrics["processed_count"] == 2
    assert metrics["output_count"] == 2
    assert metrics["error_count"] == 0
    assert checkpoint["provider_usage"] == {}
    assert checkpoint["cost_estimate"] == {}
    assert metrics["provider_usage"] == checkpoint["provider_usage"]
    assert metrics["cost_estimate"] == checkpoint["cost_estimate"]
    assert checkpoint["processing_time_seconds"] >= 0
    assert metrics["processing_time_seconds"] == checkpoint["processing_time_seconds"]


def test_stage_runner_updates_manifest_stage_status(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    StageRunner(ctx).run_stage(RunnerItemsStage)

    manifest_path = RunnerItemsStage(ctx).artifact_paths()["stage_dir"].parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["current_stage"] == "company_gate"
    assert manifest["stages"]["company_gate"] == "completed"
    assert manifest["stages"]["collect_jobs"] == "pending"

def test_stage_runner_failure_preserves_partial_checkpoint_and_manifest(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        StageRunner(ctx).run_stage(RunnerFailingStage)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")

    paths = RunnerFailingStage(ctx).artifact_paths()
    checkpoint = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()
    manifest = json.loads((paths["stage_dir"].parent / "manifest.json").read_text(encoding="utf-8"))

    assert [json.loads(line) for line in output_lines] == [{"id": "ok_1", "value": 10}]
    assert checkpoint["status"] == "partial_success"
    assert checkpoint["input_count"] == 2
    assert checkpoint["processed_count"] == 1
    assert checkpoint["output_count"] == 1
    assert checkpoint["last_processed_index"] == 0
    assert checkpoint["last_processed_id"] == "ok_1"
    assert checkpoint["errors"][0]["error_type"] == "RuntimeError"
    assert checkpoint["errors"][0]["error_message"] == "controlled stage failure"
    assert metrics["status"] == "partial_success"
    assert metrics["input_count"] == 2
    assert metrics["processed_count"] == 1
    assert metrics["output_count"] == 1
    assert metrics["error_count"] == 1
    assert checkpoint["provider_usage"] == {}
    assert checkpoint["cost_estimate"] == {}
    assert metrics["provider_usage"] == checkpoint["provider_usage"]
    assert metrics["cost_estimate"] == checkpoint["cost_estimate"]
    assert checkpoint["processing_time_seconds"] >= 0
    assert metrics["processing_time_seconds"] == checkpoint["processing_time_seconds"]
    assert manifest["current_stage"] == "freshness_gate"
    assert manifest["stages"]["freshness_gate"] == "partial_success"


def test_stage_runner_build_result_returns_stage_result(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    checkpoint = runner.run_stage(RunnerItemsStage)
    stage = RunnerItemsStage(ctx)
    metrics = StageCheckpointManager(stage).write_metrics(checkpoint)

    result = runner.build_result(checkpoint, metrics)

    assert result == {
        "run_id": ctx.run_id,
        "stage": "company_gate",
        "status": "completed",
        "checkpoint": checkpoint,
        "metrics": metrics,
    }


def test_stage_runner_read_output_returns_existing_output_jsonl(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    stage = RunnerItemsStage(ctx)
    runner.run_stage(RunnerItemsStage)

    assert runner.read_output(stage) == [
        {"id": "item_1", "value": 10},
        {"id": "item_2", "value": 20},
    ]


def test_stage_runner_read_output_returns_empty_when_missing(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    stage = RunnerItemsStage(ctx)

    assert runner.read_output(stage) == []


def test_stage_runner_read_checkpoint_returns_existing_checkpoint(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    stage = RunnerItemsStage(ctx)
    checkpoint = runner.run_stage(RunnerItemsStage)

    assert StageCheckpointManager(stage).read_checkpoint() == checkpoint


def test_stage_runner_read_checkpoint_returns_none_when_missing(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    stage = RunnerItemsStage(ctx)

    assert StageCheckpointManager(stage).read_checkpoint() is None


def test_stage_runner_resumes_after_last_processed_index(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)

    try:
        runner.run_stage(RunnerFailingStage)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")

    checkpoint = runner.run_stage(RunnerRecoveredStage)
    paths = RunnerRecoveredStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))

    assert [json.loads(line) for line in output_lines] == [
        {"id": "ok_1", "value": 10},
        {"id": "boom", "value": 20},
    ]
    assert checkpoint["status"] == "completed"
    assert checkpoint["processed_count"] == 2
    assert checkpoint["output_count"] == 2
    assert checkpoint["last_processed_index"] == 1
    assert checkpoint["last_processed_id"] == "boom"
    assert checkpoint["errors"] == []
    assert metrics["error_count"] == 0
    assert checkpoint["provider_usage"] == {}
    assert checkpoint["cost_estimate"] == {}
    assert metrics["provider_usage"] == checkpoint["provider_usage"]
    assert metrics["cost_estimate"] == checkpoint["cost_estimate"]
    assert checkpoint["processing_time_seconds"] >= 0
    assert metrics["processing_time_seconds"] == checkpoint["processing_time_seconds"]


def test_stage_runner_zero_processed_failure_stays_failed(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        StageRunner(ctx).run_stage(RunnerImmediatelyFailingStage)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")

    paths = RunnerImmediatelyFailingStage(ctx).artifact_paths()
    checkpoint = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    manifest = json.loads((paths["stage_dir"].parent / "manifest.json").read_text(encoding="utf-8"))

    assert checkpoint["status"] == "failed"
    assert checkpoint["processed_count"] == 0
    assert checkpoint["output_count"] == 0
    assert metrics["status"] == "failed"
    assert metrics["error_count"] == 1
    assert checkpoint["provider_usage"] == {}
    assert checkpoint["cost_estimate"] == {}
    assert metrics["provider_usage"] == checkpoint["provider_usage"]
    assert metrics["cost_estimate"] == checkpoint["cost_estimate"]
    assert checkpoint["processing_time_seconds"] >= 0
    assert metrics["processing_time_seconds"] == checkpoint["processing_time_seconds"]
    assert manifest["stages"]["domain_gate"] == "failed"

