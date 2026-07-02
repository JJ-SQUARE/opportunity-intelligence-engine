from oie.providers.base import ProviderClient


def test_provider_client_base_is_configured_defaults_true():
    client = ProviderClient()
    assert client.is_configured() is True
