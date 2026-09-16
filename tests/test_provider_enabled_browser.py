"""Exercise the actual provider form renderer with synthetic data only."""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).parents[1]


def test_provider_enabled_action_keeps_save_controls_and_default_state(tmp_path):
    source = (ROOT / "static/js/app-all.js").read_text(encoding="utf-8")
    renderer = source[source.index("function renderProviderEdit()"):source.index("function saveProvider(idx)")]
    protocol_helper = source[source.index("function inferProviderProtocol"):source.index("function groupVideoModels")]
    category_state = "var providerModelCategoryFilters = {};"
    toggle = source[source.index("function toggleProviderEnabledControl(idx)"):source.index("function updateCapsSection(idx)")]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1384, "height": 920})
        page.goto("about:blank")
        page.set_content('<div id="providerEditBody"></div>')
        page.evaluate("""() => {
            window.providerEditOpenIdx = 0;
            window.allProviders = [{
                id: 'synthetic-google', name: 'Synthetic Google', type: 'image',
                base_url: 'https://generativelanguage.googleapis.com',
                model: 'gemini-3-pro-image-preview', models: [], has_key: true
            }];
            window.i18nText = key => key;
            window.escHtml = window.escAttr = value => String(value || '');
            window._loadProxyConfig = window._loadUpdateInfo = () => {};
            window.saveProvider = () => {};
        }""")
        # about:blank has no storage origin; the production renderer expects one.
        page.evaluate("Object.defineProperty(window, 'localStorage', {value: {getItem: () => null}})")
        page.add_script_tag(content=protocol_helper + "\n" + category_state + "\n" + renderer + "\n" + toggle)
        page.evaluate("renderProviderEdit()")
        action = page.locator("#enToggle_0")
        expect(action).to_have_text("停止使用")
        assert page.locator("#en_0").is_checked()
        expect(page.locator('button[onclick="saveProvider(0)"]')).to_be_visible()
        action.click()
        expect(action).to_have_text("启用模型")
        assert not page.locator("#en_0").is_checked()
        action.click()
        assert page.locator("#en_0").is_checked()
        page.evaluate("allProviders[0].enabled = false; renderProviderEdit()")
        expect(page.locator("#enToggle_0")).to_have_text("启用模型")
        assert not page.locator("#en_0").is_checked()
        expect(page.locator('button[onclick="saveProvider(0)"]')).to_be_visible()
        page.screenshot(path=str(tmp_path / "provider-enabled-controls.png"), full_page=True)
        browser.close()
