from __future__ import annotations

from typing import TypeAlias

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_initial_manifest, read_manifest, update_stage_status, write_manifest
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_timing import start_timer
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_state import StageState


StageClass: TypeAlias = type[Stage]


class StageRunner:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def ensure_manifest(self) -> None:
        if read_manifest(self.ctx) is None:
            write_manifest(self.ctx, build_initial_manifest(self.ctx))

    def run_stage(self, stage_cls: StageClass, *, reset: bool = False) -> StageState:
        stage = stage_cls(self.ctx)
        checkpoint_manager = StageCheckpointManager(stage)
        stage.ensure_stage_dir()
        self.ensure_manifest()

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