"""Static contract tests for the Store three-view frontend rendering.

These tests read the committed frontend assets (no DOM runner) and lock the
fail-closed rendering contract:

- Installed / Recommended / All views exist in the Store container.
- Executable action buttons are emitted ONLY from the backend-provided
  ``item.actions`` list, filtered by an explicit allowlist (deploy).
- Planned / unverified / unknown entries display a reason and never render an
  execute button; the frontend never infers an action from status or manifest.
- External instances render a read-only hint instead of management actions.
- Every Store UI string comes from i18n keys that are bilingual (zh-CN + en).
"""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
HTML = ROOT / "static" / "index.html"
JS = ROOT / "static" / "js" / "extensions.js"
I18N = ROOT / "static" / "js" / "i18n.js"
CSS = ROOT / "static" / "css" / "extensions.css"

# The contiguous Store implementation region inside extensions.js, from the
# ownership/status helpers through the view renderer dispatcher.
STOREBLOCK_START = "function storeOwnershipLabel"
STOREBLOCK_END = "window.extensionStoreView"

BILINGUAL_PAIR = re.compile(
    r'"((?:extensions|common)\.[A-Za-z0-9_.]+)"\s*:\s*\{\s*"zh-CN":"(?:[^"\\]|\\.)*","en":"(?:[^"\\]|\\.)*"\s*\}'
)


def store_block(source) -> str:
    return source.split(STOREBLOCK_START, 1)[1].split(STOREBLOCK_END, 1)[0]


def test_store_container_has_three_views_and_data_api():
    html = HTML.read_text(encoding="utf-8")
    source = JS.read_text(encoding="utf-8")

    assert 'id="extStore"' in html
    assert 'class="extension-store-items"' in html
    for view in ("installed", "recommended", "all"):
        assert f'data-store-view="{view}"' in html
    assert "/api/extensions/store" in source
    assert "window.extensionStoreView" in source
    assert "extensionStoreData={installed:[],recommended:[],all:[]}" in source
    assert 'data-store-item="' in store_block(source)


def test_actions_are_rendered_only_from_backend_list_through_deploy_allowlist():
    source = JS.read_text(encoding="utf-8")
    block = store_block(source)

    # The single button factory must refuse anything not explicitly "deploy".
    assert "Array.isArray(item.actions)?item.actions:[]" in block
    assert "actions.map(function(action){return storeActionButton(action,item)})" in block
    assert "action!=='deploy'" in block
    # No single-language hardcoded label: button text comes from i18n.
    assert "data-i18n=\"extensions.store_deploy\">Deploy<" not in source
    assert ">Deploy</button>" not in source
    assert ">部署</button>" not in source
    # Deployment must not be staged from a recommended/managed flag either.
    assert "extension-store-action" in block


def test_unknown_partial_and_non_deployable_rows_cannot_render_deploy():
    source = JS.read_text(encoding="utf-8")
    block = store_block(source)

    assert "['planned','repository_unverified','unknown'].indexOf(status)>=0" in block
    assert "item.confidence==='unknown'||item.confidence==='partial'" in block
    assert "extension-store-readonly" in block


def test_planned_and_unverified_items_show_reasons_without_execute_buttons():
    source = JS.read_text(encoding="utf-8")
    block = store_block(source)

    for status in ("'planned'", "'repository_unverified'", "'unknown'"):
        assert status in block
    reason_keys = (
        "extensions.store_planned_reason",
        "extensions.store_unverified_reason",
        "extensions.store_unknown_reason",
    )
    for key in reason_keys:
        assert f"i18nText('{key}')" in block
    # The only button-producing function does not inspect item status at all.
    action_creator = source.split("function storeActionButton", 1)[1].split("function storeActionsHtml", 1)[0]
    assert "status" not in action_creator
    # Unknown facts are rendered only when the backend supplies them.
    assert "Array.isArray(item.unknown_facts)" in block


def test_external_instances_are_read_only_without_management_actions():
    source = JS.read_text(encoding="utf-8")
    block = store_block(source)

    assert "item.ownership==='external'" in block
    assert "i18nText('extensions.store_readonly_hint')" in block
    assert "i18nText('extensions.store_external')" in block
    assert "extension-store-item-external" in block
    # The external branch short-circuits before any action mapping, so no
    # external row can ever hold a button.
    actions_html = source.split("function storeActionsHtml", 1)[1].split("function storeRecommendationHtml", 1)[0]
    assert "item.ownership==='external'" in actions_html
    assert "return '<span class=\"extension-store-readonly\">'" in actions_html
    assert actions_html.index("extension-store-readonly") < actions_html.index("storeActionButton(action,item)")


def test_recommended_items_render_confidence_reasons_and_unknown_facts():
    source = JS.read_text(encoding="utf-8")
    block = store_block(source)

    assert "function storeRecommendationHtml" in block
    assert "item.confidence" in block
    assert "Array.isArray(item.reasons)" in block
    assert "Array.isArray(item.unknown_facts)" in block
    for key in (
        "extensions.store_confidence",
        "extensions.store_reasons_label",
        "extensions.store_unknown_facts_label",
    ):
        assert f"i18nText('{key}')" in block
    # View-level empty states stay bilingual and per-view.
    assert "extensions.store_unknown_environment" in block
    assert "extensions.store_all_empty" in block


def test_null_discovery_capabilities_render_as_unknown_not_unavailable():
    source = JS.read_text(encoding="utf-8")

    assert "value!==true&&value!==false" in source
    assert "[caps.docker_available,caps.compose_available]" in source
    assert "extensions.store_unknown_value" in source
    assert "summary.children[index].lastChild.textContent" in source


def test_store_i18n_keys_are_referenced_and_bilingual():
    i18n = I18N.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    source = JS.read_text(encoding="utf-8")

    pairs = {m.group(1) for m in BILINGUAL_PAIR.finditer(i18n)}
    referenced = set(re.findall(r'data-i18n="(extensions\.store_[A-Za-z0-9_]+|common\.all)"', html))
    referenced |= set(re.findall(r'data-i18n-aria-label="(extensions\.store_[A-Za-z0-9_]+)"', html))
    referenced |= set(re.findall(r"i18nText\('(extensions\.store_[A-Za-z0-9_]+)'\)", source))

    assert "extensions.store_installed" in referenced
    assert "extensions.store_recommended" in referenced
    assert "common.all" in referenced
    for key in sorted(referenced):
        assert key in pairs, f"missing or not bilingual (zh-CN+en) i18n key: {key}"


def test_store_css_styles_cover_rendered_markup():
    css = CSS.read_text(encoding="utf-8")
    for selector in (
        "extension-store-ownership",
        "extension-store-reason",
        "extension-store-recommendation",
        "extension-store-confidence",
        "extension-store-reasons",
        "extension-store-unknown-facts",
        "extension-store-readonly",
        "extension-store-no-actions",
        "extension-store-item-external",
    ):
        assert selector in css
