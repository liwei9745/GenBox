"""Synthetic model menu tests; no configured providers or paid API calls."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]


def test_grouped_model_drafts_preserve_scroll_focus_and_provider_scope(tmp_path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get("GENBOX_PLAYWRIGHT_EXECUTABLE")
            browser = playwright.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1438, "height": 994})
            page.set_default_timeout(5000)
            mutations = []
            ids = (
                [f"gpt-image-test-{i}" for i in range(18)]
                + [f"gemini-test-{i}" for i in range(18)]
                + ["nano-banana-test", "grok-imagine-image-test", "qwen-image-test",
                   "seedream-test", "seededit-test", "seedance-test", "veo-test",
                   "gpt-text-test", "unclassified-test", "blocked-test"]
            )
            providers = [{
                "id": provider_id, "name": provider_id, "type": "image",
                "enabled": True, "has_key": True, "endpoint_type": "openai",
                "model": ids[0], "models": ids, "capabilities": {"precision_edit": True},
                "model_capabilities": {
                    ids[0]: {"precision_edit": True, "supported_sizes": ["1024x1024"]},
                    "blocked-test": {"precision_edit": False},
                },
            } for provider_id in ["fixture-a", "fixture-b"]]

            def route_api(route):
                if route.request.method not in ("GET", "HEAD"):
                    mutations.append(route.request.url)
                if route.request.url.endswith("/api/providers"):
                    route.fulfill(status=200, json={"providers": providers})
                    return
                route.fulfill(status=404, json={"detail": "synthetic fixture only"})

            page.route("**/api/**", route_api)
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.wait_for_function("() => allProviders.length === 2")
            page.evaluate("""() => {
                document.querySelector('#pageGenerate').classList.remove('hidden');
                document.querySelector('#pageGenerate').classList.add('precision-workbench');
                document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                ensurePrecisionEditPanel();
                document.querySelector('#precisionModelPicker').open = true;
                localStorage.removeItem('genbox_precision_model_visibility_v1');
                renderPrecisionEditModelPicker();
            }""")
            trigger = page.locator("[data-precision-model-visibility-toggle]")
            trigger.click()
            menu = page.locator("#precisionModelVisibilityMenu")
            group = menu.locator('[data-precision-model-visibility-group="gemini"]')
            assert menu.locator(".precision-model-visibility-group").count() == 8
            assert menu.locator('[data-precision-model-visibility$="::blocked-test"]').count() == 0
            assert menu.locator('[data-precision-model-group-count="gemini"]').inner_text() == "19/19"
            state_before = page.evaluate("() => JSON.stringify(precisionEditSelectedModel)")
            capabilities_before = page.evaluate("() => JSON.stringify(allProviders.map(p => p.model_capabilities))")
            target = menu.locator('[data-precision-model-visibility="fixture-a::gemini-test-12"]')
            target.scroll_into_view_if_needed()
            target.focus()
            page.evaluate("""() => {
                window.fixtureMenu = document.querySelector('#precisionModelVisibilityMenu');
                window.fixtureCheckbox = document.activeElement;
                window.fixtureScroll = fixtureMenu.querySelector('.precision-model-visibility-list').scrollTop;
            }""")
            assert page.evaluate("() => fixtureScroll") > 0
            page.keyboard.press("Space")
            assert not target.is_checked()
            assert page.evaluate("""() => fixtureMenu === document.querySelector('#precisionModelVisibilityMenu')
                && fixtureCheckbox === document.activeElement
                && Math.abs(fixtureScroll - fixtureMenu.querySelector('.precision-model-visibility-list').scrollTop) < 1""")
            assert group.evaluate("el => el.indeterminate")
            assert menu.locator('[data-precision-model-group-count="gemini"]').inner_text() == "18/19"
            assert page.evaluate("() => localStorage.getItem('genbox_precision_model_visibility_v1')") is None
            assert page.evaluate("() => JSON.stringify(precisionEditSelectedModel)") == state_before
            assert page.evaluate("() => JSON.stringify(allProviders.map(p => p.model_capabilities))") == capabilities_before
            # A second toggle, using the mouse, must retain the same input and list.
            before_click = menu.locator(".precision-model-visibility-list").evaluate("el => el.scrollTop")
            target.click()
            assert target.is_checked()
            assert abs(menu.locator(".precision-model-visibility-list").evaluate("el => el.scrollTop") - before_click) < 1
            group.click()
            assert not group.is_checked()
            assert menu.locator('[data-precision-model-group-count="gemini"]').inner_text() == "0/19"
            assert page.evaluate("() => JSON.stringify(precisionEditSelectedModel)") == state_before
            menu.locator('[data-precision-model-visibility-action="cancel"]').click()
            assert page.evaluate("() => localStorage.getItem('genbox_precision_model_visibility_v1')") is None
            trigger.click()
            assert menu.locator('[data-precision-model-group-count="gemini"]').inner_text() == "19/19"
            menu.locator('[data-precision-model-visibility-action="clear"]').click()
            assert menu.locator('[data-precision-model-visibility-action="confirm"]').is_disabled()
            menu.locator('[data-precision-model-visibility-group="gpt-image"]').check()
            assert not menu.locator('[data-precision-model-visibility-action="confirm"]').is_disabled()
            menu.locator('[data-precision-model-visibility-action="confirm"]').click()
            saved = page.evaluate("() => JSON.parse(localStorage.getItem('genbox_precision_model_visibility_v1'))")
            assert saved and all(key.startswith("fixture-a::") and value is False for key, value in saved.items())
            assert page.locator("#precisionEditProviderModel option").count() == 18
            page.locator("#precisionEditProviderEndpoint").select_option("fixture-b")
            trigger.click()
            assert menu.locator('[data-precision-model-group-count="gemini"]').inner_text() == "19/19"
            for width, height in [(1438, 994), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function("""() => {
                    const r = document.querySelector('#precisionModelVisibilityMenu').getBoundingClientRect();
                    return r.right <= innerWidth && r.bottom <= innerHeight;
                }""")
                assert menu.evaluate("""el => el.scrollWidth <= el.clientWidth
                    && [...el.querySelectorAll('.precision-model-visibility-group-heading')].every(h => h.scrollWidth <= h.clientWidth)""")
                page.screenshot(path=str(tmp_path / f"model-groups-{width}.png"))
            page.keyboard.press("Escape")
            assert page.evaluate("() => !precisionModelVisibilityMenuOpen")
            assert page.evaluate("() => JSON.parse(localStorage.getItem('genbox_precision_model_visibility_v1'))") == saved
            assert not mutations, "Model display preferences must not send provider mutations or paid generation requests."
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
