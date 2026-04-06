from oie.providers.provider_registry import ProviderRegistry


def test_provider_registry_registers_components():
    registry = ProviderRegistry()

    dummy_client = object()
    registry.register_client("serpapi", dummy_client)
    registry.register_budget("serpapi", max_calls=25)
    registry.register_circuit_breaker("serpapi", failure_threshold=4)

    assert registry.get_client("serpapi") is dummy_client
    assert registry.get_budget("serpapi") is not None
    assert registry.get_budget("serpapi").max_calls == 25
    assert registry.get_circuit_breaker("serpapi") is not None
    assert registry.get_circuit_breaker("serpapi").failure_threshold == 4

def test_provider_registry_registers_default_clients():
    registry = ProviderRegistry()
    registry.register_default_clients(config={})

    assert registry.get_client("openai") is not None
    assert registry.get_client("serpapi") is not None
    assert registry.get_client("apollo") is not None
    assert registry.get_client("hunter") is not None

