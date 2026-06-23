from __future__ import annotations

from typing import Any, Dict, Iterable, List

from oie.orchestration.stage_artifacts import ensure_stage_dir, stage_artifact_paths


class Stage:
    name: str = ""
    order: int = 0

    def __init__(self, ctx: Any) -> None:
        if not self.name:
            raise ValueError("Stage.name is required")
        self.ctx = ctx

    def artifact_paths(self) -> Dict[str, Any]:
        return stage_artifact_paths(self.ctx, self.name)

    def ensure_stage_dir(self) -> Any:
        return ensure_stage_dir(self.ctx, self.name)

    def load_input(self) -> Iterable[Dict[str, Any]]:
        return []

    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return item

    def run(self) -> List[Dict[str, Any]]:
        self.ensure_stage_dir()
        return [self.process_item(item) for item in self.load_input()]
