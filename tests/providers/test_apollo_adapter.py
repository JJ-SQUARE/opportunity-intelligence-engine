from oie.providers.adapters.apollo_adapter import ApolloAdapter


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "organization": {
                "industry": "Software",
                "estimated_num_employees": "51-200",
                "linkedin_url": "https://linkedin.com/company/acme",
                "short_description": "Builds software",
            }
        }


def test_apollo_adapter_calls_requests_get(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.apollo_adapter.requests.get", fake_get)

    adapter = ApolloAdapter(
        config={
            "api_key": "apollo-test-key",
            "timeout_seconds": 12,
        }
    )

    result = adapter.enrich_company_by_domain("acme.com")

    assert result["organization"]["industry"] == "Software"
    assert captured["url"] == adapter.enrich_url
    assert captured["params"]["domain"] == "acme.com"
    assert captured["headers"]["X-Api-Key"] == "apollo-test-key"
    assert "Authorization" not in captured["headers"]
    assert "Cache-Control" not in captured["headers"]
    assert captured["headers"]["accept"] == "application/json"
    assert captured["timeout"] == 12.0


def test_apollo_adapter_normalizes_domain_for_enrichment(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.apollo_adapter.requests.get", fake_get)

    adapter = ApolloAdapter(
        config={
            "api_key": "apollo-test-key",
        }
    )

    adapter.enrich_company_by_domain("https://www.Acme.com/path?q=1")

    assert captured["params"]["domain"] == "acme.com"


def test_apollo_adapter_people_search_uses_json_payload(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.apollo_adapter.requests.post", fake_post)

    adapter = ApolloAdapter(
        config={
            "api_key": "apollo-test-key",
            "timeout_seconds": 8,
        }
    )

    adapter.search_people_by_domain_and_titles(
        "https://www.acme.com/jobs",
        ["CTO", "  VP Engineering  ", ""],
    )

    assert captured["url"] == adapter.people_search_url
    assert captured["json"]["q_organization_domains_list"] == ["acme.com"]
    assert captured["json"]["person_titles"] == ["CTO", "VP Engineering"]
    assert captured["json"]["page"] == 1
    assert captured["json"]["per_page"] == 10
    assert captured["headers"]["X-Api-Key"] == "apollo-test-key"
    assert "Authorization" not in captured["headers"]
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 8.0


def test_apollo_adapter_strips_api_key_whitespace():
    adapter = ApolloAdapter(
        config={
            "api_key": "  apollo-test-key\n",
            "timeout_seconds": 12,
        }
    )

    assert adapter.api_key == "apollo-test-key"


def test_apollo_adapter_uses_x_api_key_header_name(monkeypatch):
    captured = {}

    class _DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"organization": {"name": "Acme"}}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.apollo_adapter.requests.get", fake_get)

    adapter = ApolloAdapter(
        config={
            "api_key": "apollo-test-key",
            "timeout_seconds": 12,
        }
    )

    adapter.enrich_company_by_domain("acme.com")

    assert captured["headers"]["X-Api-Key"] == "apollo-test-key"
    assert "x-api-key" not in captured["headers"]


def test_apollo_adapter_is_configured_true_with_api_key():
    adapter = ApolloAdapter(config={"api_key": "test-key"})
    assert adapter.is_configured() is True


def test_apollo_adapter_is_configured_false_without_api_key(monkeypatch):
    monkeypatch.delenv("APOLLO_API_KEY", raising=False)
    adapter = ApolloAdapter(config={})
    assert adapter.is_configured() is False
