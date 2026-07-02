from unittest.mock import Mock, patch

from oie.providers.adapters.hubspot_adapter import HubSpotAdapter


def test_search_contact_by_email_returns_existing_contact():
    adapter = HubSpotAdapter(config={"api_key": "test-token"})

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {
                "id": "123",
                "properties": {
                    "email": "jane@acme.com",
                    "firstname": "Jane",
                    "lastname": "Doe",
                },
            }
        ]
    }

    with patch.object(adapter, "_post_raw", return_value=mock_response) as mock_post:
        result = adapter.search_contact_by_email("jane@acme.com")

    assert result is not None
    assert result["id"] == "123"

    args = mock_post.call_args[0]
    payload = args[1]
    assert args[0] == "/crm/v3/objects/contacts/search"
    assert payload["filterGroups"][0]["filters"][0]["propertyName"] == "email"
    assert payload["filterGroups"][0]["filters"][0]["value"] == "jane@acme.com"


def test_search_company_by_domain_returns_existing_company():
    adapter = HubSpotAdapter(config={"api_key": "test-token"})

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {
                "id": "456",
                "properties": {
                    "name": "Acme",
                    "domain": "acme.com",
                },
            }
        ]
    }

    with patch.object(adapter, "_post_raw", return_value=mock_response) as mock_post:
        result = adapter.search_company_by_domain("acme.com")

    assert result is not None
    assert result["id"] == "456"

    args = mock_post.call_args[0]
    payload = args[1]
    assert args[0] == "/crm/v3/objects/companies/search"
    assert payload["filterGroups"][0]["filters"][0]["propertyName"] == "domain"
    assert payload["filterGroups"][0]["filters"][0]["value"] == "acme.com"


def test_search_task_by_subject_returns_existing_task():
    adapter = HubSpotAdapter(config={"api_key": "test-token"})

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {
                "id": "789",
                "properties": {
                    "hs_task_subject": "Revisar reporte: Jane Doe (Acme)",
                },
            }
        ]
    }

    with patch.object(adapter, "_post_raw", return_value=mock_response) as mock_post:
        result = adapter.search_task_by_subject("Revisar reporte: Jane Doe (Acme)")

    assert result is not None
    assert result["id"] == "789"

    args = mock_post.call_args[0]
    payload = args[1]
    assert args[0] == "/crm/v3/objects/tasks/search"
    assert payload["filterGroups"][0]["filters"][0]["propertyName"] == "hs_task_subject"
    assert payload["filterGroups"][0]["filters"][0]["value"] == "Revisar reporte: Jane Doe (Acme)"


def test_hubspot_adapter_is_configured_true_with_api_key():
    adapter = HubSpotAdapter(config={"api_key": "test-token"})
    assert adapter.is_configured() is True


def test_hubspot_adapter_is_configured_false_without_api_key(monkeypatch):
    monkeypatch.delenv("HUBSPOT_BEARER_TOKEN", raising=False)
    adapter = HubSpotAdapter(config={})
    assert adapter.is_configured() is False
