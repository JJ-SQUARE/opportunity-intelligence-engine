from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from oie.orchestration.stage_artifacts import StageArtifactPaths, ensure_stage_dir, stage_artifact_paths
from oie.orchestration.stage_item import StageItem


class Stage:
    name: str = ""
    order: int = 0

    def __init__(self, ctx: Any) -> None:
        if not self.name:
            raise ValueError("Stage.name is required")
        self.ctx = ctx

    def artifact_paths(self) -> StageArtifactPaths:
        return stage_artifact_paths(self.ctx, self.name)

    def ensure_stage_dir(self) -> Path:
        return ensure_stage_dir(self.ctx, self.name)

    def load_input(self) -> Iterable[StageItem]:
        return []

    def process_item(self, item: StageItem) -> StageItem:
        return item

    def run(self) -> list[StageItem]:
        self.ensure_stage_dir()
        return [self.process_item(item) for item in self.load_input()]
