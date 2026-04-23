from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.serpapi_search_service import SerpAPISearchService


def test_serpapi_search_service_uses_provider_execution():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"serpapi": 2},
                "clients": {
                    "serpapi": {
                        "api_key": "fake-key"
                    }
                },
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("serpapi")
    client.search_google_jobs = lambda query, location=None, num=10: {
        "jobs_results": [{"title": "Data Engineer"}],
        "query": query,
        "location": location,
    }

    service = SerpAPISearchService(ctx, control)
    result = service.search_google_jobs("data engineer", location="Mexico", num=5)

    assert result["jobs_results"][0]["title"] == "Data Engineer"
    assert ctx.budgets["serpapi"]["used_calls"] == 1
    assert ctx.metrics["serpapi_search_requests"] == 1


def test_serpapi_search_service_respects_dry_run():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"serpapi": 2},
                "clients": {
                    "serpapi": {
                        "api_key": "fake-key"
                    }
                },
            }
        },
        flags={"dry_run": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = SerpAPISearchService(ctx, control)
    result = service.search_google_jobs("data engineer", location="Mexico", num=5)

    assert result == {}
    assert ctx.budgets["serpapi"]["used_calls"] == 0
    assert ctx.metrics["serpapi_search_skipped_blocked"] is True


def test_serpapi_search_service_google_search_tracks_metric():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"serpapi": 2},
                "clients": {
                    "serpapi": {
                        "api_key": "fake-key"
                    }
                },
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("serpapi")
    client.search_google = lambda query, num=10: {
        "organic_results": [{"title": "Tekton Labs - Official Website"}],
        "query": query,
    }

    service = SerpAPISearchService(ctx, control)
    result = service.search_google("tekton labs official website", num=5)

    assert result["organic_results"][0]["title"] == "Tekton Labs - Official Website"
    assert ctx.budgets["serpapi"]["used_calls"] == 1
    assert ctx.metrics["serpapi_search_requests"] == 1
    assert ctx.metrics["serpapi_search_google_requests"] == 1
