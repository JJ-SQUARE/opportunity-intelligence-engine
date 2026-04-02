import requests

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionError, ProviderExecutionService


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def _raise_429(*args, **kwargs):
    raise requests.exceptions.HTTPError("429 Too Many Requests", response=_FakeResponse(429))


def test_provider_execution_service_tracks_rate_limit():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"serpapi": 10},
                "retry_policy": {
                    "serpapi": {
                        "max_attempts": 1,
                        "base_delay_seconds": 0.0,
                        "backoff_multiplier": 1.0,
                    }
                },
            }
        },
        flags={},
    )
    pcs = ProviderControlService(ctx)
    pcs.initialize()

    svc = ProviderExecutionService(ctx, pcs)

    try:
        svc.execute("serpapi", "search_google_jobs", _raise_429, "python remote", cost=1)
    except ProviderExecutionError:
        pass

    assert ctx.metrics["serpapi_errors_rate_limit"] == 1
    assert ctx.metrics["serpapi_search_google_jobs_errors_rate_limit"] == 1

    matching_events = [
        e for e in ctx.provider_events
        if e.get("provider") == "serpapi" and e.get("event_type") == "rate_limit"
    ]
    assert matching_events, "Expected a rate_limit provider event"
