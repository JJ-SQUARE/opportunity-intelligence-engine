from __future__ import annotations

from oie.orchestration.pipeline_stages import validate_pipeline_stage
from oie.orchestration.stage_runner import StageClass


class StageRegistry:
    def __init__(self) -> None:
        self._stages: dict[str, StageClass] = {}

    def register(self, stage_cls: StageClass) -> None:
        validate_pipeline_stage(stage_cls.name)
        self._stages[stage_cls.name] = stage_cls

    def get(self, stage_name: str) -> StageClass:
        validate_pipeline_stage(stage_name)
        try:
            return self._stages[stage_name]
        except KeyError as exc:
            raise KeyError(f"Stage is not registered: {stage_name}") from exc

    def names(self) -> list[str]:
        return list(self._stages)
