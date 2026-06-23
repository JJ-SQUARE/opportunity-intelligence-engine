from pathlib import Path

import pytest

from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_base import Stage


class DummyStage(Stage):
    name = "collect_jobs"
    order = 1

    def load_input(self):
        return [
            {"value": 1},
            {"value": 2},
        ]

    def process_item(self, item):
        return {"value": item["value"] * 10}


def test_stage_run_processes_items_and_creates_stage_dir(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    stage = DummyStage(ctx)
    output = stage.run()

    assert output == [{"value": 10}, {"value": 20}]
    assert Path(ctx.paths["stage_dirs"]["collect_jobs"]).exists()


def test_stage_requires_name(tmp_path):
    class NamelessStage(Stage):
        pass

    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    with pytest.raises(ValueError, match="Stage.name is required"):
        NamelessStage(ctx)
