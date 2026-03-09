from __future__ import annotations

from typing import Any, Callable, Dict

from oie.orchestration.run_context import RunContext
from oie.services.http_cache_service import HTTPCacheService


class CachedProviderService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.cache = HTTPCacheService(ctx)

    def execute_cached(
        self,
        namespace: str,
        cache_payload: Dict[str, Any],
        fn: Callable[..., Dict[str, Any]],
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        if self.ctx.flags.get("cache_only"):
            cached = self.cache.get(namespace, cache_payload)
            if cached is not None:
                return cached
            self.ctx.metrics["cache_only_misses"] = self.ctx.metrics.get("cache_only_misses", 0) + 1
            return {}

        cached = self.cache.get(namespace, cache_payload)
        if cached is not None:
            return cached

        result = fn(*args, **kwargs) or {}
        if isinstance(result, dict):
            self.cache.set(namespace, cache_payload, result)
        return result
