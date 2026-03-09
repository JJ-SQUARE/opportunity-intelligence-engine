from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from oie.orchestration.run_context import RunContext


class HTTPCacheService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        cache_dir = (
            self.ctx.config.get("cache", {}).get("base_dir")
            or "data/http_cache"
        )
        self.base_dir = Path(cache_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, namespace: str, payload: Dict[str, Any]) -> str:
        raw = json.dumps(
            {
                "namespace": namespace,
                "payload": payload,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _build_path(self, namespace: str, payload: Dict[str, Any]) -> Path:
        key = self._make_key(namespace, payload)
        namespace_dir = self.base_dir / namespace
        namespace_dir.mkdir(parents=True, exist_ok=True)
        return namespace_dir / f"{key}.json"

    def get(self, namespace: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        path = self._build_path(namespace, payload)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.ctx.metrics["http_cache_hits"] = self.ctx.metrics.get("http_cache_hits", 0) + 1
            return data
        except Exception:
            self.ctx.metrics["http_cache_read_errors"] = self.ctx.metrics.get("http_cache_read_errors", 0) + 1
            return None

    def set(self, namespace: str, payload: Dict[str, Any], value: Dict[str, Any]) -> None:
        path = self._build_path(namespace, payload)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.metrics["http_cache_writes"] = self.ctx.metrics.get("http_cache_writes", 0) + 1
