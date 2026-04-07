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
    assert captured["headers"]["x-api-key"] == "apollo-test-key"
    assert captured["headers"]["accept"] == "application/json"
    assert captured["timeout"] == 12.0
