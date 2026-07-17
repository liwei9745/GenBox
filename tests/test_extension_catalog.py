from extensions.catalog import public_catalog


def test_catalog_ids_are_unique_and_non_gemini_ids_are_unchanged():
    items = public_catalog()["items"]
    ids = [item["id"] for item in items]
    assert all(ids)
    assert len(ids) == len(set(ids))
    assert {
        item["id"] for item in items
        if item["repository"] not in {"liwei9745/gemini2api", "xwteam/gemini2api"}
    } == {
        "chatgpt2api",
        "grok2api",
        "aiclient2api",
        "mimocode2api",
        "flow2api",
        "kiro2api",
        "account-token-tools",
        "free-residential-ip-proxy-controller",
        "aimili-vpngate",
        "socks5-proxy",
    }


def test_gemini_repositories_have_fixed_planned_catalog_ids():
    items_by_repository = {item["repository"]: item for item in public_catalog()["items"]}
    expected_ids = {
        "liwei9745/gemini2api": "gemini2api-liwei9745",
        "xwteam/gemini2api": "gemini2api-xwteam",
    }

    for repository, catalog_id in expected_ids.items():
        item = items_by_repository[repository]
        assert item["id"] == catalog_id
        assert item["status"] == "planned"
        assert item["deployable"] is False


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
