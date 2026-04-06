from oie.models.provider_event import ProviderEventRecord


def test_provider_event_record_to_dict_includes_optional_fields():
    event = ProviderEventRecord(
        provider="serpapi",
        event_type="rate_limit",
        status_code=429,
        message="Too Many Requests",
        metadata={"operation_name": "search_google"},
    )

    payload = event.to_dict()

    assert payload["provider"] == "serpapi"
    assert payload["event_type"] == "rate_limit"
    assert payload["status_code"] == 429
    assert payload["message"] == "Too Many Requests"
    assert payload["metadata"]["operation_name"] == "search_google"
