from oie.orchestration.run_context import RunContext
from oie.services.http_cache_service import HTTPCacheService


def test_http_cache_service_writes_and_reads(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}},
        flags={},
    )
    service = HTTPCacheService(ctx)

    namespace = "apollo_company_enrichment"
    payload = {"domain": "acme.com"}
    value = {"organization": {"industry": "Software"}}

    service.set(namespace, payload, value)
    loaded = service.get(namespace, payload)

    assert loaded == value
    assert ctx.metrics["http_cache_writes"] == 1
    assert ctx.metrics["http_cache_hits"] == 1
