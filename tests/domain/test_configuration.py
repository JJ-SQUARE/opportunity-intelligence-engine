from oie.domain.configuration import (
    AccountConfiguration,
    HubSpotDeliveryConfiguration,
    ICPProfile,
    QueryConfiguration,
    RunConfiguration,
    UserConfiguration,
)


def test_run_configuration_groups_domain_configuration_objects():
    account = AccountConfiguration(account_id="acc_1", account_name="Tekton")
    user = UserConfiguration(user_id="user_1", email="user@example.com")
    delivery = HubSpotDeliveryConfiguration(
        hubspot_user_id="123",
        hubspot_owner_id="456",
        hubspot_company_id="789",
        hubspot_credentials_ref="hubspot/test",
    )
    icp = ICPProfile(
        profile_id="asd",
        name="ASD",
        weights={"industry": 0.4},
        rules={"min_score": 75},
    )
    query = QueryConfiguration(
        query="python engineer remote latam",
        source="serpapi",
        location="LATAM",
    )

    config = RunConfiguration(
        account=account,
        user=user,
        hubspot_delivery=delivery,
        icp_profiles=[icp],
        queries=[query],
        flags={"dry_run": True},
        mode="dry-run",
    )

    assert config.account is account
    assert config.user is user
    assert config.hubspot_delivery is delivery
    assert config.icp_profiles == [icp]
    assert config.queries == [query]
    assert config.flags == {"dry_run": True}
    assert config.mode == "dry-run"


def test_run_configuration_defaults_are_isolated():
    first = RunConfiguration()
    second = RunConfiguration()

    first.icp_profiles.append(ICPProfile(profile_id="taas", name="TaaS"))
    first.queries.append(QueryConfiguration(query="react engineer"))

    assert second.icp_profiles == []
    assert second.queries == []
