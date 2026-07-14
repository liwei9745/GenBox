from extensions.catalog import public_catalog


def test_only_chatgpt2api_is_deployable():
    catalog = public_catalog()
    deployable = [item for item in catalog["items"] if item.get("deployable")]
    assert [item["id"] for item in deployable] == ["chatgpt2api"]


def test_proxy_tools_are_declared_as_providers_only():
    catalog = public_catalog()
    proxies = [item for item in catalog["items"] if item["category"] == "proxy_network"]
    assert len(proxies) == 3
    assert all(item["provides_proxy"] and not item["deployable"] for item in proxies)


def test_unverified_repository_cannot_be_deployed():
    item = next(item for item in public_catalog()["items"] if item["id"] == "kiro2api")
    assert item["status"] == "repository_unverified"
    assert item["deployable"] is False
