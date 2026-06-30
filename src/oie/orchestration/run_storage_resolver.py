from __future__ import annotations

from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext


def configure_ctx_for_run_storage(ctx: RunContext, run_id: str) -> RunContext:
    ctx.run_id = run_id
    run_dir = f"{ctx.paths['runs_base_dir']}/{run_id}"
    ctx.paths["run_dir"] = run_dir
    ctx.paths["manifest_path"] = f"{run_dir}/manifest.json"
    ctx.paths["stage_dirs"] = {
        stage: f"{run_dir}/{index:02d}_{stage}"
        for index, stage in enumerate(PIPELINE_STAGES, start=1)
    }
    return ctx
