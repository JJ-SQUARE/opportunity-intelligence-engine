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
from oie.orchestration.stage_result import StageResult, build_stage_result
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

    result = build_stage_result(checkpoint, metrics)

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

    assert StageCheckpointManager(stage).read_output() == [
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

    assert StageCheckpointManager(stage).read_output() == []


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

def test_load_checkpoint_payload_rejects_unknown_stage():
    checkpoint = {
        "run_id": "run_1",
        "stage": "unknown_stage",
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
    except ValueError as exc:
        assert str(exc) == "Unknown pipeline stage: unknown_stage"
    else:
        raise AssertionError("Expected ValueError")


def test_load_checkpoint_payload_rejects_unknown_status():
    checkpoint = {
        "run_id": "run_1",
        "stage": "collect_jobs",
        "status": "unknown_status",
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
    except ValueError as exc:
        assert str(exc) == "Unknown run status: unknown_status"
    else:
        raise AssertionError("Expected ValueError")


def test_stage_checkpoint_manager_rejects_invalid_checkpoint_before_write(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    stage = RunnerDummyStage(ctx)
    manager = StageCheckpointManager(stage)
    checkpoint = manager.initial_checkpoint()
    checkpoint["stage"] = "unknown_stage"

    try:
        manager.write_checkpoint(checkpoint)
    except ValueError as exc:
        assert str(exc) == "Unknown pipeline stage: unknown_stage"
    else:
        raise AssertionError("Expected ValueError")

    assert not stage.artifact_paths()["checkpoint"].exists()

def test_write_json_file_creates_parent_directories(tmp_path):
    from oie.orchestration.stage_io import read_json_file, write_json_file

    path = tmp_path / "nested" / "checkpoint.json"
    payload = {"run_id": "run_1", "status": "completed"}

    write_json_file(path, payload)

    assert path.exists()
    assert read_json_file(path) == payload
    assert not (path.parent / ".checkpoint.json.tmp").exists()


def test_append_jsonl_item_creates_parent_directories(tmp_path):
    from oie.orchestration.stage_io import append_jsonl_item, read_jsonl_file

    path = tmp_path / "nested" / "output.jsonl"
    item = {"id": "item_1", "value": 10, "metadata": {}}

    append_jsonl_item(path, item)

    assert path.exists()
    assert read_jsonl_file(path) == [item]


def test_read_jsonl_file_reports_invalid_line_number(tmp_path):
    from oie.orchestration.stage_io import read_jsonl_file

    path = tmp_path / "output.jsonl"
    path.write_text('{"id": "item_1"}\nnot-json\n', encoding="utf-8")

    try:
        read_jsonl_file(path)
    except ValueError as exc:
        assert str(exc) == f"Invalid JSONL at {path}:2"
    else:
        raise AssertionError("Expected ValueError")

def test_stage_runner_rerun_completed_stage_does_not_duplicate_output(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    runner = StageRunner(ctx)

    first_checkpoint = runner.run_stage(RunnerItemsStage)
    second_checkpoint = runner.run_stage(RunnerItemsStage)
    paths = RunnerItemsStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert [json.loads(line) for line in output_lines] == [
        {"id": "item_1", "value": 10},
        {"id": "item_2", "value": 20},
    ]
    assert first_checkpoint["processed_count"] == 2
    assert second_checkpoint["processed_count"] == 2
    assert second_checkpoint["output_count"] == 2
    assert second_checkpoint["last_processed_index"] == 1


def test_stage_runner_rejects_resume_when_checkpoint_output_count_exceeds_artifact(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    runner.run_stage(RunnerItemsStage)

    paths = RunnerItemsStage(ctx).artifact_paths()
    paths["output"].write_text(
        json.dumps({"id": "item_1", "value": 10}) + "\n",
        encoding="utf-8",
    )

    try:
        runner.run_stage(RunnerItemsStage)
    except ValueError as exc:
        assert str(exc) == (
            "Checkpoint/output mismatch for company_gate: "
            "checkpoint output_count=2, artifact output_count=1"
        )
    else:
        raise AssertionError("Expected ValueError")


def test_stage_runner_rejects_resume_when_artifact_output_count_exceeds_checkpoint(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    runner.run_stage(RunnerItemsStage)

    paths = RunnerItemsStage(ctx).artifact_paths()
    with paths["output"].open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps({"id": "extra", "value": 999}) + "\n")

    try:
        runner.run_stage(RunnerItemsStage)
    except ValueError as exc:
        assert str(exc) == (
            "Checkpoint/output mismatch for company_gate: "
            "checkpoint output_count=2, artifact output_count=3"
        )
    else:
        raise AssertionError("Expected ValueError")

class RunnerShrunkInputStage(Stage):
    name = "company_gate"
    order = 2

    def load_input(self):
        return [
            {"id": "item_1", "value": 1},
        ]

    def process_item(self, item):
        return {
            "id": item["id"],
            "value": item["value"] * 10,
        }


def test_stage_runner_rejects_resume_when_input_shrinks_below_processed_count(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    runner = StageRunner(ctx)
    runner.run_stage(RunnerItemsStage)

    try:
        runner.run_stage(RunnerShrunkInputStage)
    except ValueError as exc:
        assert str(exc) == (
            "Checkpoint/input mismatch for company_gate: "
            "processed_count=2, input_count=1"
        )
    else:
        raise AssertionError("Expected ValueError")

def test_stage_registry_registers_and_resolves_stage_class():
    from oie.orchestration.stage_registry import StageRegistry

    registry = StageRegistry()
    registry.register(RunnerItemsStage)

    assert registry.get("company_gate") is RunnerItemsStage
    assert registry.names() == ["company_gate"]


def test_stage_registry_rejects_unknown_pipeline_stage():
    from oie.orchestration.stage_registry import StageRegistry

    class UnknownStage(Stage):
        name = "unknown_stage"
        order = 99

    registry = StageRegistry()

    try:
        registry.register(UnknownStage)
    except ValueError as exc:
        assert str(exc) == "Unknown pipeline stage: unknown_stage"
    else:
        raise AssertionError("Expected ValueError")


def test_stage_registry_rejects_unregistered_known_stage_lookup():
    from oie.orchestration.stage_registry import StageRegistry

    registry = StageRegistry()

    try:
        registry.get("collect_jobs")
    except KeyError as exc:
        assert str(exc) == "'Stage is not registered: collect_jobs'"
    else:
        raise AssertionError("Expected KeyError")

def test_stage_registry_registers_many_stage_classes():
    from oie.orchestration.stage_registry import StageRegistry

    registry = StageRegistry()
    registry.register_many([RunnerDummyStage, RunnerItemsStage])

    assert registry.get("collect_jobs") is RunnerDummyStage
    assert registry.get("company_gate") is RunnerItemsStage
    assert registry.names() == ["collect_jobs", "company_gate"]


def test_stage_registry_has_validates_and_reports_presence():
    from oie.orchestration.stage_registry import StageRegistry

    registry = StageRegistry()
    registry.register(RunnerDummyStage)

    assert registry.has("collect_jobs") is True
    assert registry.has("company_gate") is False

    try:
        registry.has("unknown_stage")
    except ValueError as exc:
        assert str(exc) == "Unknown pipeline stage: unknown_stage"
    else:
        raise AssertionError("Expected ValueError")

def test_collect_jobs_stage_loads_collection_service_jobs(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.services.collection_service import CollectionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
                "apply_url": "https://acme.test/apply/1",
            },
            {
                "title": "Data Engineer",
                "company": "Beta",
                "source": "linkedin_serpapi",
            },
        ],
    )

    items = CollectJobsStage(ctx).load_input()

    assert items == [
        {
            "id": "https://acme.test/jobs/1",
            "value": {
                "title": "Backend Engineer",
                "company": "Acme",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
                "apply_url": "https://acme.test/apply/1",
            },
            "metadata": {
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
                "apply_url": "https://acme.test/apply/1",
            },
        },
        {
            "id": "collected_job_2",
            "value": {
                "title": "Data Engineer",
                "company": "Beta",
                "source": "linkedin_serpapi",
            },
            "metadata": {
                "source": "linkedin_serpapi",
                "job_url": None,
                "apply_url": None,
            },
        },
    ]


def test_stage_runner_runs_collect_jobs_stage(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.services.collection_service import CollectionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(CollectJobsStage)
    paths = CollectJobsStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "collect_jobs"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1
    assert [json.loads(line) for line in output_lines] == [
        {
            "id": "https://acme.test/jobs/1",
            "value": {
                "title": "Backend Engineer",
                "company": "Acme",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
            "metadata": {
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
                "apply_url": None,
            },
        }
    ]

def test_normalize_jobs_stage_loads_collect_jobs_output(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.services.collection_service import CollectionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )

    StageRunner(ctx).run_stage(CollectJobsStage)

    items = NormalizeJobsStage(ctx).load_input()

    assert items == [
        {
            "id": "https://acme.test/jobs/1",
            "value": {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
            "metadata": {
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
                "apply_url": None,
            },
        }
    ]


def test_stage_runner_runs_normalize_jobs_stage(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.services.collection_service import CollectionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "description": "Fully remote full-time backend role",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )

    StageRunner(ctx).run_stage(CollectJobsStage)
    checkpoint = StageRunner(ctx).run_stage(NormalizeJobsStage)
    paths = NormalizeJobsStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "company_gate"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "https://acme.test/jobs/1"
    assert output["value"]["is_remote"] is True
    assert output["value"]["is_full_time"] is True
    assert output["value"]["remote_flag"] is True
    assert output["metadata"] == {
        "source": "google_jobs",
        "job_url": "https://acme.test/jobs/1",
        "apply_url": None,
    }


def test_normalize_jobs_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        NormalizeJobsStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "NormalizeJobsStage item value must be a job object."
    else:
        raise AssertionError("Expected TypeError")

def test_job_intelligence_stage_loads_normalize_jobs_output(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
    from oie.services.collection_service import CollectionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )

    StageRunner(ctx).run_stage(CollectJobsStage)
    StageRunner(ctx).run_stage(NormalizeJobsStage)

    items = JobIntelligenceStage(ctx).load_input()

    assert len(items) == 1
    assert items[0]["id"] == "https://acme.test/jobs/1"
    assert items[0]["value"]["is_remote"] is True
    assert items[0]["metadata"] == {
        "source": "google_jobs",
        "job_url": "https://acme.test/jobs/1",
        "apply_url": None,
    }


def test_stage_runner_runs_job_intelligence_stage(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
    from oie.services.collection_service import CollectionService
    from oie.services.job_intelligence_service import JobIntelligenceService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )

    monkeypatch.setattr(
        JobIntelligenceService,
        "enrich_jobs",
        lambda self, jobs: [{**jobs[0], "job_ai_confidence": 0.9}],
    )

    StageRunner(ctx).run_stage(CollectJobsStage)
    StageRunner(ctx).run_stage(NormalizeJobsStage)
    checkpoint = StageRunner(ctx).run_stage(JobIntelligenceStage)
    paths = JobIntelligenceStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "freshness_gate"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "https://acme.test/jobs/1"
    assert output["value"]["job_ai_confidence"] == 0.9
    assert output["metadata"] == {
        "source": "google_jobs",
        "job_url": "https://acme.test/jobs/1",
        "apply_url": None,
    }


def test_job_intelligence_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.job_intelligence_stage import JobIntelligenceStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        JobIntelligenceStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "JobIntelligenceStage item value must be a job object."
    else:
        raise AssertionError("Expected TypeError")

def test_company_gate_stage_loads_job_intelligence_output(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
    from oie.orchestration.company_gate_stage import CompanyGateStage
    from oie.services.collection_service import CollectionService
    from oie.services.job_intelligence_service import JobIntelligenceService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )
    monkeypatch.setattr(JobIntelligenceService, "enrich_jobs", lambda self, jobs: jobs)

    StageRunner(ctx).run_stage(CollectJobsStage)
    StageRunner(ctx).run_stage(NormalizeJobsStage)
    StageRunner(ctx).run_stage(JobIntelligenceStage)

    items = CompanyGateStage(ctx).load_input()

    assert len(items) == 1
    assert items[0]["id"] == "https://acme.test/jobs/1"
    assert items[0]["value"]["company"] == "Acme"


def test_stage_runner_runs_company_gate_stage(monkeypatch, tmp_path):
    from oie.orchestration.collect_jobs_stage import CollectJobsStage
    from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
    from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
    from oie.orchestration.company_gate_stage import CompanyGateStage
    from oie.services.collection_service import CollectionService
    from oie.services.job_intelligence_service import JobIntelligenceService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    monkeypatch.setattr(
        CollectionService,
        "collect",
        lambda self: [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "description": "Fully remote contract backend role",
                "source": "google_jobs",
                "job_url": "https://acme.test/jobs/1",
            },
        ],
    )
    monkeypatch.setattr(JobIntelligenceService, "enrich_jobs", lambda self, jobs: jobs)

    StageRunner(ctx).run_stage(CollectJobsStage)
    StageRunner(ctx).run_stage(NormalizeJobsStage)
    StageRunner(ctx).run_stage(JobIntelligenceStage)
    checkpoint = StageRunner(ctx).run_stage(CompanyGateStage)
    paths = CompanyGateStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "domain_gate"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["company"] == "Acme"
    assert output["value"]["total_openings"] == 1
    assert output["value"]["remote_jobs"] == 1
    assert output["value"]["contractor_jobs"] == 1
    assert output["metadata"]["company"] == "Acme"


def test_company_gate_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.company_gate_stage import CompanyGateStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        CompanyGateStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "CompanyGateStage item value must be a job object."
    else:
        raise AssertionError("Expected TypeError")

def test_ai_company_gate_stage_advances_ai_approved_company(tmp_path):
    from oie.orchestration.ai_company_gate_stage import AICompanyGateStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "ai_company_gate_company_type": "end_client",
            "ai_company_gate_relevance": "high",
            "ai_company_gate_should_advance": True,
        },
        "metadata": {"company": "Acme"},
    }

    output = AICompanyGateStage(ctx).process_item(item)

    assert output["id"] == "Acme"
    assert output["value"]["ai_company_gate_status"] == "advanced"
    assert "company_identity_ai_discarded" not in output["value"]


def test_ai_company_gate_stage_rejects_ai_identified_job_board(tmp_path):
    from oie.orchestration.ai_company_gate_stage import AICompanyGateStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    item = {
        "id": "Job Board Co",
        "value": {
            "company": "Job Board Co",
            "ai_company_gate_company_type": "job_board",
            "ai_company_gate_relevance": "low",
            "ai_company_gate_should_advance": False,
        },
        "metadata": {"company": "Job Board Co"},
    }

    output = AICompanyGateStage(ctx).process_item(item)

    assert output["value"]["company_identity_ai_discarded"] is True
    assert output["value"]["ai_company_gate_status"] == "rejected"
    assert ctx.metrics["companies_rejected_by_ai_job_board"] == 1


def test_ai_company_gate_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.ai_company_gate_stage import AICompanyGateStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        AICompanyGateStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "AICompanyGateStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_company_identity_ai_stage_loads_ai_company_gate_output(tmp_path):
    from oie.orchestration.ai_company_gate_stage import AICompanyGateStage
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "ai_company_gate_status": "advanced",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(AICompanyGateStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert CompanyIdentityAIStage(ctx).load_input() == [item]


def test_stage_runner_runs_company_identity_ai_stage(monkeypatch, tmp_path):
    from oie.orchestration.ai_company_gate_stage import AICompanyGateStage
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.company_identity_ai_service import CompanyIdentityAIService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "ai_company_gate_status": "advanced",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(AICompanyGateStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        CompanyIdentityAIService,
        "enrich_companies",
        lambda self, companies: [
            {
                **companies[0],
                "company_identity_ai_valid": True,
                "ai_company_identity_confidence": 0.92,
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(CompanyIdentityAIStage)
    paths = CompanyIdentityAIStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "icp_match"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["company_identity_ai_valid"] is True
    assert output["value"]["ai_company_identity_confidence"] == 0.92


def test_company_identity_ai_stage_skips_rejected_ai_gate_company(tmp_path):
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Job Board Co",
        "value": {
            "company": "Job Board Co",
            "ai_company_gate_status": "rejected",
            "company_identity_ai_discarded": True,
        },
        "metadata": {"company": "Job Board Co"},
    }

    output = CompanyIdentityAIStage(ctx).process_item(item)

    assert output == item


def test_company_identity_ai_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        CompanyIdentityAIStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "CompanyIdentityAIStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_domain_resolution_stage_loads_company_identity_ai_output(tmp_path):
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "company_identity_ai_valid": True,
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyIdentityAIStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert DomainResolutionStage(ctx).load_input() == [item]


def test_stage_runner_runs_domain_resolution_stage(monkeypatch, tmp_path):
    from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.domain_resolution_service import DomainResolutionService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "company_identity_ai_valid": True,
            "ai_company_gate_domain_guess": "acme.test",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyIdentityAIStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        DomainResolutionService,
        "resolve_domains",
        lambda self, companies: [
            {
                **companies[0],
                "resolved_domain": "acme.test",
                "domain_resolution_status": "accepted",
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(DomainResolutionStage)
    paths = DomainResolutionStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "lead_generation"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["resolved_domain"] == "acme.test"
    assert output["value"]["domain_resolution_status"] == "accepted"


def test_domain_resolution_stage_skips_discarded_company(tmp_path):
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Bad Co",
        "value": {
            "company": "Bad Co",
            "company_identity_ai_discarded": True,
        },
        "metadata": {"company": "Bad Co"},
    }

    output = DomainResolutionStage(ctx).process_item(item)

    assert output == item


def test_domain_resolution_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        DomainResolutionStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "DomainResolutionStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_company_enrichment_stage_loads_domain_resolution_output(tmp_path):
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "resolved_domain": "acme.com",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(DomainResolutionStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert CompanyEnrichmentStage(ctx).load_input() == [item]


def test_stage_runner_runs_company_enrichment_stage(monkeypatch, tmp_path):
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage
    from oie.orchestration.domain_resolution_stage import DomainResolutionStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.company_enrichment_service import CompanyEnrichmentService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "resolved_domain": "acme.com",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(DomainResolutionStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"
    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        CompanyEnrichmentService,
        "enrich_companies",
        lambda self, companies: [
            {
                **companies[0],
                "industry": "Software",
                "company_size": "51-200",
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(CompanyEnrichmentStage)
    paths = CompanyEnrichmentStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "delivery"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["industry"] == "Software"
    assert output["value"]["company_size"] == "51-200"


def test_company_enrichment_stage_skips_discarded_company(tmp_path):
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Bad Co",
        "value": {
            "company": "Bad Co",
            "company_identity_ai_discarded": True,
        },
        "metadata": {"company": "Bad Co"},
    }

    output = CompanyEnrichmentStage(ctx).process_item(item)

    assert output == item


def test_company_enrichment_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        CompanyEnrichmentStage(ctx).process_item({"id": "bad", "value": "not-a-dict"})
    except TypeError as exc:
        assert str(exc) == "CompanyEnrichmentStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_company_classification_stage_loads_company_enrichment_output(tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "industry": "Software",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyEnrichmentStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert CompanyClassificationStage(ctx).load_input() == [item]


def test_stage_runner_runs_company_classification_stage(monkeypatch, tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage
    from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.company_classification_service import CompanyClassificationService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "industry": "Software",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyEnrichmentStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        CompanyClassificationService,
        "classify_companies",
        lambda self, companies: [
            {
                **companies[0],
                "company_type": "SaaS",
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(CompanyClassificationStage)
    paths = CompanyClassificationStage(ctx).artifact_paths()

    output = json.loads(paths["output"].read_text().splitlines()[0])

    assert checkpoint["stage"] == "company_classification"
    assert checkpoint["status"] == "completed"
    assert output["value"]["company_type"] == "SaaS"


def test_company_classification_stage_skips_discarded_company(tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    item = {
        "id": "Bad",
        "value": {
            "company": "Bad",
            "company_identity_ai_discarded": True,
        },
        "metadata": {},
    }

    assert CompanyClassificationStage(ctx).process_item(item) == item


def test_company_classification_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        CompanyClassificationStage(ctx).process_item(
            {
                "id": "bad",
                "value": "not-a-dict",
            }
        )
    except TypeError as exc:
        assert str(exc) == "CompanyClassificationStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_opportunity_scoring_stage_loads_company_classification_output(tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "company_type_ai": "end_client",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyClassificationStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert OpportunityScoringStage(ctx).load_input() == [item]


def test_stage_runner_runs_opportunity_scoring_stage(monkeypatch, tmp_path):
    from oie.orchestration.company_classification_stage import CompanyClassificationStage
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.opportunity_scoring_service import OpportunityScoringService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "company_type_ai": "end_client",
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyClassificationStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        OpportunityScoringService,
        "score_companies",
        lambda self, companies: [
            {
                **companies[0],
                "opportunity_score": 87,
                "opportunity_label": "high",
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(OpportunityScoringStage)
    paths = OpportunityScoringStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "opportunity_scoring"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["opportunity_score"] == 87
    assert output["value"]["opportunity_label"] == "high"


def test_opportunity_scoring_stage_skips_discarded_company(tmp_path):
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Rejected Co",
        "value": {
            "company": "Rejected Co",
            "company_identity_ai_discarded": True,
        },
        "metadata": {"company": "Rejected Co"},
    }

    output = OpportunityScoringStage(ctx).process_item(item)

    assert output == item


def test_opportunity_scoring_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        OpportunityScoringStage(ctx).process_item(
            {
                "id": "bad",
                "value": "not-a-dict",
            }
        )
    except TypeError as exc:
        assert str(exc) == "OpportunityScoringStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_company_limit_stage_loads_opportunity_scoring_output(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "opportunity_score": 87,
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(OpportunityScoringStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert CompanyLimitStage(ctx).load_input() == [item]


def test_stage_runner_runs_company_limit_stage(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage
    from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={"limit": 1},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "opportunity_score": 87,
            "classification_confidence_ai": 0.9,
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(OpportunityScoringStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    checkpoint = StageRunner(ctx).run_stage(CompanyLimitStage)
    paths = CompanyLimitStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "company_limit"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["company"] == "Acme"
    assert ctx.metrics["companies_limit_requested"] == 1
    assert ctx.metrics["companies_limit_applied"] == 1


def test_company_limit_stage_excludes_company_when_limit_zero(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={"limit": 0},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "opportunity_score": 87,
        },
        "metadata": {"company": "Acme"},
    }

    output = CompanyLimitStage(ctx).process_item(item)

    assert output["value"]["company_limit_excluded"] is True
    assert ctx.metrics["companies_limit_applied"] == 0


def test_company_limit_stage_skips_discarded_company(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={"limit": 0},
    )
    item = {
        "id": "Rejected Co",
        "value": {
            "company": "Rejected Co",
            "company_identity_ai_discarded": True,
        },
        "metadata": {"company": "Rejected Co"},
    }

    output = CompanyLimitStage(ctx).process_item(item)

    assert output == item


def test_company_limit_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        CompanyLimitStage(ctx).process_item(
            {
                "id": "bad",
                "value": "not-a-dict",
            }
        )
    except TypeError as exc:
        assert str(exc) == "CompanyLimitStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")

def test_lead_generation_stage_loads_company_limit_output(tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage
    from oie.orchestration.lead_generation_stage import LeadGenerationStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "resolved_domain": "acme.com",
            "opportunity_score": 87,
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyLimitStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    assert LeadGenerationStage(ctx).load_input() == [item]


def test_stage_runner_runs_lead_generation_stage(monkeypatch, tmp_path):
    from oie.orchestration.company_limit_stage import CompanyLimitStage
    from oie.orchestration.lead_generation_stage import LeadGenerationStage
    from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
    from oie.services.lead_generation_service import LeadGenerationService

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Acme",
        "value": {
            "company": "Acme",
            "resolved_domain": "acme.com",
            "domain_validation_status": "accepted",
            "opportunity_score": 87,
        },
        "metadata": {"company": "Acme"},
    }

    manager = StageCheckpointManager(CompanyLimitStage(ctx))
    checkpoint = manager.initial_checkpoint(status="completed")
    checkpoint["input_count"] = 1
    checkpoint["processed_count"] = 1
    checkpoint["output_count"] = 1
    checkpoint["last_processed_index"] = 0
    checkpoint["last_processed_id"] = "Acme"

    manager.append_output(item)
    manager.write_checkpoint(checkpoint)

    monkeypatch.setattr(
        LeadGenerationService,
        "generate_leads",
        lambda self, companies: [
            {
                "company": companies[0]["company"],
                "company_key": "cmp_acme",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
            }
        ],
    )

    checkpoint = StageRunner(ctx).run_stage(LeadGenerationStage)
    paths = LeadGenerationStage(ctx).artifact_paths()
    output_lines = paths["output"].read_text(encoding="utf-8").splitlines()

    assert checkpoint["stage"] == "lead_contact_generation"
    assert checkpoint["status"] == "completed"
    assert checkpoint["input_count"] == 1
    assert checkpoint["processed_count"] == 1

    output = json.loads(output_lines[0])
    assert output["id"] == "Acme"
    assert output["value"]["company"]["company"] == "Acme"
    assert output["value"]["lead_generation_skipped"] is False
    assert output["value"]["leads"] == [
        {
            "company": "Acme",
            "company_key": "cmp_acme",
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
        }
    ]


def test_lead_generation_stage_skips_excluded_company(tmp_path):
    from oie.orchestration.lead_generation_stage import LeadGenerationStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    item = {
        "id": "Excluded Co",
        "value": {
            "company": "Excluded Co",
            "company_limit_excluded": True,
        },
        "metadata": {"company": "Excluded Co"},
    }

    output = LeadGenerationStage(ctx).process_item(item)

    assert output["value"]["company"]["company"] == "Excluded Co"
    assert output["value"]["leads"] == []
    assert output["value"]["lead_generation_skipped"] is True


def test_lead_generation_stage_rejects_non_object_stage_value(tmp_path):
    from oie.orchestration.lead_generation_stage import LeadGenerationStage

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    try:
        LeadGenerationStage(ctx).process_item(
            {
                "id": "bad",
                "value": "not-a-dict",
            }
        )
    except TypeError as exc:
        assert str(exc) == "LeadGenerationStage item value must be a company object."
    else:
        raise AssertionError("Expected TypeError")
