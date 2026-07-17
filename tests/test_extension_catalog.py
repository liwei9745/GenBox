from extensions.catalog import public_catalog


GEMINI_REPOSITORY_IDS = {
    "liwei9745/gemini2api": "gemini2api-liwei9745",
    "xwteam/gemini2api": "gemini2api-xwteam",
}

NON_GEMINI_REPOSITORY_IDS = {
    "yukkcat/chatgpt2api": "chatgpt2api",
    "chenyme/grok2api": "grok2api",
    "justlovemaki/AIClient2API": "aiclient2api",
    "Sliverkiss/mimocode2api": "mimocode2api",
    "TheSmallHanCat/flow2api": "flow2api",
    "luohui1/kiro2api": "kiro2api",
    "": "account-token-tools",
    "a6216abcd/Free-Residential-IP-Proxy-Controller": "free-residential-ip-proxy-controller",
    "baoweise-bot/aimili-vpngate": "aimili-vpngate",
    "yukkcat/socks5-proxy": "socks5-proxy",
}


def test_catalog_ids_are_unique_and_non_gemini_ids_are_unchanged():
    items = public_catalog()["items"]
    ids = [item["id"] for item in items]
    assert all(isinstance(item_id, str) and item_id.strip() for item_id in ids)
    assert len(ids) == len(set(ids))
    assert {
        item["repository"]: item["id"] for item in items
        if item["repository"] not in GEMINI_REPOSITORY_IDS
    } == NON_GEMINI_REPOSITORY_IDS


def test_gemini_repositories_have_fixed_planned_catalog_ids():
    gemini_items = [item for item in public_catalog()["items"] if item["repository"] in GEMINI_REPOSITORY_IDS]
    assert len(gemini_items) == 2
    assert {item["repository"] for item in gemini_items} == set(GEMINI_REPOSITORY_IDS)
    assert {item["repository"]: item["id"] for item in gemini_items} == GEMINI_REPOSITORY_IDS
    assert all(item["status"] == "planned" and item["deployable"] is False for item in gemini_items)


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
