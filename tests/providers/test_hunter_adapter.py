from oie.providers.adapters.hunter_adapter import HunterAdapter


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "data": {
                "emails": [
                    {"value": "jane@acme.com", "position": "CTO", "first_name": "Jane"}
                ]
            }
        }


def test_hunter_adapter_calls_requests_get(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.hunter_adapter.requests.get", fake_get)

    adapter = HunterAdapter(
        config={
            "api_key": "hunter-test-key",
            "timeout_seconds": 11,
        }
    )

    result = adapter.search_domain_contacts("acme.com")

    assert result["data"]["emails"][0]["value"] == "jane@acme.com"
    assert captured["params"]["domain"] == "acme.com"
    assert captured["params"]["api_key"] == "hunter-test-key"
    assert captured["timeout"] == 11.0


def test_hunter_adapter_is_configured_true_with_api_key():
    adapter = HunterAdapter(config={"api_key": "test-key"})
    assert adapter.is_configured() is True


def test_hunter_adapter_is_configured_false_without_api_key(monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    adapter = HunterAdapter(config={})
    assert adapter.is_configured() is False
