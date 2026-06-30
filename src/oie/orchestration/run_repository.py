from __future__ import annotations

from pathlib import Path

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunConfiguration, RunContext
from oie.orchestration.run_manifest import RunManifest, list_run_manifests, read_run_manifest, write_manifest
from oie.orchestration.stage_io import read_json_file, write_json_file


class RunRepository:

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _read_manifest(self, run_id: str):
        return read_run_manifest(self.ctx, run_id)

    @classmethod
    def create(cls) -> "RunRepository":
        return cls(RunContext.create())

    def list_summaries(
        self,
        account_id: str | None = None,
        user_id: str | None = None,
    ) -> list[JSONPayload]:
        summaries = []
        for manifest in list_run_manifests(self.ctx):
            account = manifest.get("account", {}) or {}
            user = manifest.get("user", {}) or {}
            if account_id is not None and account.get("account_id") != account_id:
                continue
            if user_id is not None and user.get("user_id") != user_id:
                continue
            summaries.append(
                {
                    "run_id": manifest["run_id"],
                    "status": manifest["status"],
                    "current_stage": manifest["current_stage"],
                    "created_at": manifest["created_at"],
                    "updated_at": manifest["updated_at"],
                    "account": dict(account),
                    "user": dict(user),
                    "hubspot_delivery": dict(manifest.get("hubspot_delivery", {}) or {}),
                }
            )
        return summaries

    def read_status(self, run_id: str) -> JSONPayload | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        return {
            "run_id": manifest["run_id"],
            "status": manifest["status"],
            "current_stage": manifest["current_stage"],
        }

    def read_stages(self, run_id: str) -> list[JSONPayload] | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        return [
            {"stage": stage_name, "status": status}
            for stage_name, status in manifest.get("stages", {}).items()
        ]

    def read_stage(self, run_id: str, stage_name: str) -> JSONPayload | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        stages = manifest.get("stages", {})
        if stage_name not in stages:
            return None
        return {"stage": stage_name, "status": stages[stage_name]}

    def read_errors(self, run_id: str) -> list[JSONPayload] | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        return list(manifest.get("errors", []))

    def read_metrics_summary(self, run_id: str) -> JSONPayload | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        stages = manifest.get("stages", {})
        return {
            "run_id": manifest["run_id"],
            "stage_count": len(stages),
            "error_count": len(manifest.get("errors", [])),
            "status_counts": {
                status: list(stages.values()).count(status)
                for status in sorted(set(stages.values()))
            },
        }

    def read_detail(self, run_id: str) -> JSONPayload | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        return dict(manifest)

    def write_detail(self, manifest: RunManifest) -> Path:
        return write_manifest(self.ctx, manifest)

    def build_configuration(self) -> RunConfiguration:
        return RunConfiguration(
            **dict(self.ctx.config),
            flags=dict(self.ctx.flags),
            mode=self.ctx.mode,
        )

    def write_configuration(self, configuration_path: Path, configuration: RunConfiguration) -> Path:
        write_json_file(configuration_path, dict(configuration))
        return configuration_path

    def read_configuration(self, run_id: str) -> RunConfiguration | None:
        manifest = self._read_manifest(run_id)
        if manifest is None:
            return None
        config_path = manifest.get("config_path")
        if not config_path:
            return None
        configuration = read_json_file(Path(config_path))
        if configuration is None:
            return None
        return RunConfiguration(**configuration)
