from oie.providers.adapters.openai_adapter import OpenAIAdapter


def test_openai_adapter_is_configured_true_with_env_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    adapter = OpenAIAdapter()
    assert adapter.is_configured() is True


def test_openai_adapter_is_configured_false_without_env_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OIE_OPENAI_API_KEY", raising=False)
    adapter = OpenAIAdapter()
    assert adapter.is_configured() is False
