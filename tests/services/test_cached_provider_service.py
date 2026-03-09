from oie.orchestration.run_context import RunContext
from oie.services.cached_provider_service import CachedProviderService


def test_cached_provider_service_uses_cache_on_second_call(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}},
        flags={},
    )
    service = CachedProviderService(ctx)

    calls = {"count": 0}

    def fake_fn():
        calls["count"] += 1
        return {"ok": True}

    payload = {"domain": "acme.com"}

    result_1 = service.execute_cached("apollo_company_enrichment", payload, fake_fn)
    result_2 = service.execute_cached("apollo_company_enrichment", payload, fake_fn)

    assert result_1 == {"ok": True}
    assert result_2 == {"ok": True}
    assert calls["count"] == 1
