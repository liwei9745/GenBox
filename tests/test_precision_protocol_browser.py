"""Synthetic browser acceptance for model-scoped precision connections."""

from copy import deepcopy
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

import main
from config import ProviderConfig, PrecisionEditProfile


ROOT = Path(__file__).parents[1]
NANO = "nano-banana-2-2k"
GPT = "gpt-image-2.5-c"
GEMINI = "gemini-3.1-flash-image"
JSON_PROFILE = "openai_images_edits_json_data_url_single_source_image"


def _fixture_provider():
    return ProviderConfig(
        id="synthetic-gateway",
        name="Synthetic image gateway",
        type="image",
        api_key="synthetic-test-only",
        base_url="https://api.velapi.cc/v1",
        model=GPT,
        models=[GPT, NANO],
        endpoint_type="openai",
        precision_edit_profile=PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE,
        capabilities={"precision_edit": True, "t2i": True, "i2i": True},
        extra={
            "model_capabilities": {
                GPT: {
                    "precision_edit": True,
                    "supported_sizes": ["1024x1024", "2048x1152", "2048x2048"],
                },
                NANO: {"precision_edit": True, "supported_sizes": ["2048x2048", "2752x1536"]},
            },
            "precision_model_overrides": {
                NANO: {
                    "protocol": "gemini",
                    "profile": "gemini_generate_content",
                    "size_model": GEMINI,
                    "capabilities": {
                        "precision_edit": True,
                        "supported_sizes": ["2048x2048", "2752x1536"],
                    },
                }
            },
        },
    )


def _public_provider(provider):
    return {
        "id": provider.id,
        "name": provider.name,
        "type": provider.type,
        "model": provider.model,
        "models": provider.models,
        "enabled": True,
        "has_key": True,
        "endpoint_type": provider.endpoint_type,
        "precision_edit_profile": provider.precision_edit_profile.value,
        "capabilities": provider.capabilities,
        "model_capabilities": provider.extra["model_capabilities"],
        "precision_size_catalog": main._public_precision_size_catalog(provider),
    }


def test_precision_protocol_actual_browser_interactions(tmp_path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    provider = _fixture_provider()
    original_gpt = deepcopy(provider.extra["model_capabilities"][GPT])
    calls = []
    unexpected_mutations = []
    fail_next_save = False
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get("GENBOX_PLAYWRIGHT_EXECUTABLE")
            browser = playwright.chromium.launch(
                headless=True,
                **({"executable_path": executable} if executable else {}),
            )
            page = browser.new_page(viewport={"width": 1394, "height": 920})
            page.on("dialog", lambda dialog: dialog.accept())

            def route_request(route):
                nonlocal fail_next_save
                request = route.request
                if not request.url.startswith(origin + "/"):
                    route.abort()
                    return
                path = urlsplit(request.url).path
                if not path.startswith("/api/"):
                    route.continue_()
                    return
                body = request.post_data_json if request.post_data else None
                calls.append({"path": path, "method": request.method, "body": body})
                if path == "/api/providers" and request.method == "GET":
                    route.fulfill(json={"providers": [_public_provider(provider)]})
                elif path.endswith("/precision-protocol") and request.method == "POST":
                    if fail_next_save:
                        fail_next_save = False
                        route.fulfill(status=503, json={"detail": {"message": "Synthetic save rejected"}})
                        return
                    overrides = provider.extra.setdefault("precision_model_overrides", {})
                    if body["protocol"] == "inherit":
                        overrides.pop(body["model"], None)
                    else:
                        overrides[body["model"]] = {
                            "protocol": body["protocol"],
                            "profile": body.get("profile") or (
                                "gemini_generate_content" if body["protocol"] == "gemini" else JSON_PROFILE
                            ),
                            "size_model": body.get("size_model") or GEMINI,
                            "capabilities": {
                                "precision_edit": True,
                                "supported_sizes": ["2048x2048", "2752x1536"],
                            },
                        }
                    route.fulfill(json={"ok": True})
                elif path.endswith("/precision-preflight") and request.method == "POST":
                    route.fulfill(json={"ok": True, "message": "Synthetic local check; zero upstream calls.", "upstream_requests": 0})
                elif path == "/api/generate" and request.method == "POST":
                    route.fulfill(json={"generation_id": None, "provider_states": {}})
                elif request.method not in ("GET", "HEAD"):
                    unexpected_mutations.append(path)
                    route.fulfill(status=404, json={"detail": "Unexpected synthetic mutation"})
                else:
                    route.fulfill(status=404, json={"detail": "Synthetic fixture only"})

            page.route("**/*", route_request)
            page.add_init_script("localStorage.setItem('genbox_precision_quick_start_v1', 'seen')")
            page.goto(origin + "/static/index.html", wait_until="networkidle")
            page.evaluate("""() => {
                document.querySelector('#pageDashboard').classList.add('hidden');
                ['#loginPage', '#welcomePage', '#setupWizard', '#onboardingTour'].forEach(selector => {
                    const blocker = document.querySelector(selector);
                    if (blocker) blocker.classList.add('hidden');
                });
                document.querySelector('#pageGenerate').classList.remove('hidden');
                document.querySelector('#pageGenerate').classList.add('precision-workbench');
                document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                currentMode = 'precision_edit';
                ensurePrecisionEditPanel();
                cancelPrecisionQuickStart();
                const image = document.createElement('canvas');
                image.width = 1024; image.height = 1024;
                const context = image.getContext('2d');
                context.fillStyle = '#178b76'; context.fillRect(0, 0, 1024, 1024);
                context.fillStyle = '#ffd26e'; context.fillRect(256, 256, 512, 512);
                loadPrecisionEditSourceImage(image.toDataURL('image/png'), 'Synthetic source', 1024, 1024);
            }""")
            page.evaluate("() => loadProviders()")
            page.locator("#precisionModelPicker").evaluate("el => el.open = true")
            order = page.locator(".precision-model-picker-body").evaluate("""el => {
                    const ids = [
                        'precisionEditProviderEndpoint',
                        'precisionEditModelVisibility',
                        'precisionEditProviderModel',
                        'precisionProtocolControls',
                    ];
                    return ids.map(id => {
                        const node = document.getElementById(id);
                        const item = node && (node.tagName === 'SELECT' ? node.parentElement : node);
                        return item ? Number(getComputedStyle(item).order || 0) : -1;
                    });
            }""")
            assert order == sorted(order), order
            assert page.locator('[data-precision-step]').count() == 0
            assert page.locator('.precision-step-badge').count() == 0
            assert "先选择模型端点" in page.locator('[data-i18n="creator.precision_start_model"]').first.inner_text()
            page.evaluate("""() => {
                const endpoint = document.getElementById('precisionEditProviderEndpoint');
                const model = document.getElementById('precisionEditProviderModel');
                endpoint.value = '';
                model.value = '';
                precisionEditModelPickerReady = false;
                updatePrecisionEditAuthorizationControl();
            }""")
            expect(page.locator("#precisionProtocolSelect")).to_be_disabled()
            expect(page.locator("#precisionProtocolCurrent")).to_contain_text("先选择模型端点")
            page.evaluate("() => renderPrecisionEditModelPicker()")
            page.locator("#precisionEditProviderModel").select_option(f"{provider.id}::{NANO}")
            expect(page.locator("#precisionProtocolSelect")).to_have_value("gemini")
            expect(page.locator("#precisionProtocolCurrent")).to_contain_text("手动")

            # Previously applied settings must be undoable without changing GPT.
            page.locator("#btnPrecisionProtocolReset").click()
            expect(page.locator("#precisionProtocolSelect")).to_have_value("inherit")
            expect(page.locator("#precisionProtocolSelect")).to_be_enabled()
            expect(page.locator("#btnPrecisionProtocolCheck")).to_be_enabled()
            expect(page.locator("#precisionProtocolCurrent")).to_contain_text("JSON")
            assert provider.extra["model_capabilities"][GPT] == original_gpt

            # The selected non-square model preset survives repeated UI updates.
            page.locator("#btnPrecisionSizeResize").click()
            non_square = page.locator("#precisionResizePreset").evaluate("""el => {
                const option = Array.from(el.options).find(option => !option.hidden
                    && option.value.startsWith('model:') && option.dataset.size
                    && option.dataset.size.split('x')[0] !== option.dataset.size.split('x')[1]);
                return option && {value: option.value, size: option.dataset.size};
            }""")
            assert non_square, "No non-square Nano model preset is selectable"
            page.locator("#precisionResizePreset").select_option(non_square["value"])
            page.locator("#precisionResizePrompt").fill("Preserve the square and extend the teal background.")
            page.evaluate("() => { updatePrecisionEditControls(); updatePrecisionResizeCapabilityUI(); }")
            expect(page.locator("#precisionResizePreset")).to_have_value(non_square["value"])
            assert page.evaluate("() => getPrecisionResizeTargetSize()") == non_square["size"]

            # Drafts block Generate and a rejected save leaves the draft editable.
            page.locator("#precisionProtocolSelect").select_option("openai")
            assert page.evaluate("() => getPrecisionEditReadiness().ready") is False
            expect(page.locator("#btnGen")).to_be_disabled()
            fail_next_save = True
            page.locator("#btnPrecisionProtocolApply").click()
            expect(page.locator("#btnPrecisionProtocolApply")).to_be_enabled()
            expect(page.locator("#precisionProtocolSelect")).to_have_value("openai")
            assert page.locator("#precisionProtocolControls").get_attribute("data-dirty") == "true"
            page.locator("#btnPrecisionProtocolApply").click()
            expect(page.locator("#precisionProtocolControls")).to_have_attribute("data-dirty", "false")
            expect(page.locator("#precisionProtocolSelect")).to_be_enabled()
            expect(page.locator("#btnPrecisionProtocolReset")).to_be_enabled()
            expect(page.locator("#btnPrecisionProtocolCheck")).to_be_enabled()

            # Switching providers/models must restore their own protocol and sizes.
            page.locator("#precisionEditProviderModel").select_option(f"{provider.id}::{GPT}")
            expect(page.locator("#precisionProtocolSelect")).to_have_value("inherit")
            assert page.evaluate("() => getPrecisionResizeCapability().sizes['1024x1024']") is True
            page.locator("#precisionEditProviderModel").select_option(f"{provider.id}::{NANO}")
            expect(page.locator("#precisionProtocolSelect")).to_have_value("openai")
            assert provider.extra["model_capabilities"][GPT] == original_gpt
            page.locator("#btnPrecisionProtocolCheck").click()
            expect(page.locator("#precisionProtocolStatus")).to_contain_text("zero upstream")

            screenshots = []
            for width, height in [(1394, 920), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.locator("#precisionProtocolSelect").scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                bounds = page.locator(".precision-edit-inspector").evaluate("""el => {
                    const outer = el.getBoundingClientRect();
                    const ids = ['precisionProtocolControls', 'precisionProtocolSelect',
                        'precisionResizePreset', 'precisionProtocolCurrent'];
                    return {outer: {left: outer.left, right: outer.right}, width: innerWidth,
                        children: ids.map(id => { const node = document.getElementById(id);
                            const r = node.getBoundingClientRect();
                            return {id, left: r.left, right: r.right, scroll: node.scrollWidth,
                                client: node.clientWidth}; })};
                }""")
                assert bounds["outer"]["left"] >= -1, bounds
                assert bounds["outer"]["right"] <= width + 1, bounds
                for item in bounds["children"]:
                    assert item["left"] >= bounds["outer"]["left"] - 1, bounds
                    assert item["right"] <= bounds["outer"]["right"] + 1, bounds
                    assert item["scroll"] <= item["client"] + 1, bounds
                screenshot = tmp_path / f"precision-protocol-{width}.png"
                page.screenshot(path=str(screenshot))
                screenshots.append(str(screenshot.resolve()))

            # Capture actual mocked generation payload and a user-confirmed retry.
            page.set_viewport_size({"width": 1394, "height": 920})
            page.evaluate("""pid => {
                currentMode = 't2i';
                selectedProviders = [pid];
                promptMode = 'simple';
                document.getElementById('txtPrompt').value = 'Synthetic colored square';
                document.getElementById('selModel').value = '_global';
                document.getElementById('chkEnhance').checked = false;
                document.getElementById('chkContinuous').checked = false;
                onImageModelChange(pid, 'nano-banana-2-2k');
                doGenerate();
            }""", provider.id)
            page.wait_for_function("() => lastGenContext && lastGenContext.mode === 't2i'")
            page.wait_for_timeout(100)
            generated = [item for item in calls if item["path"] == "/api/generate"]
            assert generated and generated[-1]["body"]["provider_settings"][provider.id]["model"] == NANO
            page.evaluate("pid => retryProvider(pid + '_0', pid)", provider.id)
            generated = [item for item in calls if item["path"] == "/api/generate"]
            assert len(generated) == 2
            assert generated[-1]["body"]["provider_settings"][provider.id]["model"] == NANO
            assert provider.model == GPT
            assert not unexpected_mutations
            print("Synthetic screenshot paths: " + ", ".join(screenshots))
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
