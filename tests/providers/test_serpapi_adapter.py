from oie.providers.adapters.serpapi_adapter import SerpAPIAdapter


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"jobs_results": [{"title": "Backend Engineer"}]}


def test_serpapi_adapter_calls_requests_get(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("oie.providers.adapters.serpapi_adapter.requests.get", fake_get)

    adapter = SerpAPIAdapter(
        config={
            "api_key": "test-key",
            "timeout_seconds": 9,
        }
    )

    result = adapter.search_google_jobs("python developer", location="Mexico", num=5)

    assert result["jobs_results"][0]["title"] == "Backend Engineer"
    assert captured["params"]["engine"] == "google_jobs"
    assert captured["params"]["q"] == "python developer"
    assert captured["params"]["location"] == "Mexico"
    assert captured["params"]["num"] == 5
    assert captured["params"]["api_key"] == "test-key"
    assert captured["timeout"] == 9.0


def test_serpapi_adapter_is_configured_true_with_api_key():
    adapter = SerpAPIAdapter(config={"api_key": "test-key"})
    assert adapter.is_configured() is True


def test_serpapi_adapter_is_configured_false_without_api_key():
    adapter = SerpAPIAdapter(config={})
    assert adapter.is_configured() is False
