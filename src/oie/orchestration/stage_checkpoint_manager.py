from __future__ import annotations

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint import build_initial_checkpoint, read_checkpoint_file
from oie.orchestration.stage_state import StageState


class StageCheckpointManager:
    def __init__(self, stage: Stage) -> None:
        self.stage = stage

    def initial_checkpoint(self, status: str = "running") -> StageState:
        return build_initial_checkpoint(self.stage.ctx, self.stage, status)

    def read_checkpoint(self) -> StageState | None:
        paths = self.stage.artifact_paths()
        return read_checkpoint_file(paths["checkpoint"])
