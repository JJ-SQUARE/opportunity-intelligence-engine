from __future__ import annotations

from typing import TypeAlias

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import update_stage_status
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_timing import start_timer
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_state import StageState
from pathlib import Path


StageClass: TypeAlias = type[Stage]


class StageRunner:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def run_stage(self, stage_cls: StageClass, *, reset: bool = False) -> StageState:
        stage = stage_cls(self.ctx)
        checkpoint_manager = StageCheckpointManager(stage)
        stage.ensure_stage_dir()
        # FIX: ensure manifest exists before any stage execution (required by tests)
        from oie.orchestration.run_manifest import read_manifest, build_initial_manifest, write_manifest

        manifest_path = Path(self.ctx.paths["manifest_path"])
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = read_manifest(self.ctx)
        if manifest is None:
            manifest = build_initial_manifest(self.ctx)
            write_manifest(self.ctx, manifest)

        if reset:
            checkpoint_manager.reset_artifacts()
        update_stage_status(self.ctx, stage.name, "running")
        inputs = list(stage.load_input())
        checkpoint, start_index = checkpoint_manager.prepare_checkpoint(len(inputs))
        start_time = start_timer()

        try:
            for index, item in enumerate(inputs[start_index:], start=start_index):
                output_item = stage.process_item(item)
                checkpoint_manager.append_output(output_item)
                checkpoint_manager.record_processed_item(checkpoint, index, output_item)
                checkpoint_manager.write_checkpoint(checkpoint)
        except Exception as exc:
            failure_status = checkpoint_manager.record_stage_failure(checkpoint, exc, start_time)
            checkpoint_manager.write_checkpoint(checkpoint)
            checkpoint_manager.write_metrics(checkpoint)
            update_stage_status(self.ctx, stage.name, failure_status)
            raise

        checkpoint_manager.record_stage_completion(checkpoint, start_time)
        checkpoint_manager.write_checkpoint(checkpoint)
        checkpoint_manager.write_metrics(checkpoint)
        update_stage_status(self.ctx, stage.name, "completed")
        return checkpoint