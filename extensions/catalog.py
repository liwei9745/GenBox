"""Extension catalog metadata. Executability is derived from capabilities."""

from extensions.capabilities import catalog_item_is_deployable

CATALOG = [
    {
        "id": "chatgpt2api",
        "name": "chatgpt2api",
        "repository": "yukkcat/chatgpt2api",
        "category": "api_gateway",
        "status": "available",
        "integrates_proxy": True,
    },
    *[
        {
            "id": {
                "liwei9745/gemini2api": "gemini2api-liwei9745",
                "xwteam/gemini2api": "gemini2api-xwteam",
            }.get(repository, repository.rsplit("/", 1)[-1].lower()),
            "name": repository.rsplit("/", 1)[-1],
            "repository": repository,
            "category": "api_gateway",
            "status": "planned",
            "integrates_proxy": True,
        }
        for repository in [
            "chenyme/grok2api",
            "justlovemaki/AIClient2API",
            "liwei9745/gemini2api",
            "Sliverkiss/mimocode2api",
            "TheSmallHanCat/flow2api",
            "xwteam/gemini2api",
        ]
    ],
    {
        "id": "kiro2api",
        "name": "kiro2api",
        "repository": "luohui1/kiro2api",
        "category": "api_gateway",
        "status": "repository_unverified",
        "integrates_proxy": True,
    },
    {
        "id": "account-token-tools",
        "name": "账号注册与 Token 管理",
        "repository": "",
        "category": "account_token",
        "status": "planned",
        "integrates_proxy": True,
    },
    *[
        {
            "id": repository.rsplit("/", 1)[-1].lower(),
            "name": repository.rsplit("/", 1)[-1],
            "repository": repository,
            "category": "proxy_network",
            "status": "planned",
            "provides_proxy": True,
        }
        for repository in [
            "a6216abcd/Free-Residential-IP-Proxy-Controller",
            "baoweise-bot/aimili-vpngate",
            "yukkcat/socks5-proxy",
        ]
    ],
]


def public_catalog() -> dict:
    return {
        "categories": [
            {"id": "api_gateway", "name": "API 代理与模型网关"},
            {"id": "account_token", "name": "账号注册与 Token 管理"},
            {"id": "proxy_network", "name": "代理网络与节点工具"},
        ],
        "items": [
            {
                **item,
                "deployable": catalog_item_is_deployable(item["id"], item["repository"]),
            }
            for item in CATALOG
        ],
    }
