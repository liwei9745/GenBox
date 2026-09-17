"""Synthetic UI acceptance; no provider traffic or real credentials."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def page():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1384, "height": 920})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "synthetic"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html",
                      wait_until="domcontentloaded")
            page.evaluate("""async () => {
                // Startup discovery must settle before installing the synthetic catalog.
                await window.providersLoadPromise;
                window._loadProxyConfig = window._loadUpdateInfo = () => {};
                window.allProviders = [{
                    id:'synthetic', name:'Demo Image', type:'image', enabled:true,
                    has_key:true, model:'demo-image', models:[],
                    base_url:'https://example.invalid/v1', endpoint_type:'openai'
                }];
                window.providerEditOpenIdx = 0;
            }""")
            yield page
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_provider_steps_preserve_drafts_and_preset_requires_confirmation(page, tmp_path):
    page.evaluate("""() => {
        document.getElementById('providerModal').classList.add('show');
        document.getElementById('providerModal').style.display = 'flex';
        renderProviderEdit();
    }""")
    form = page.locator(".provider-guided-form")
    expect(form).to_have_count(1)
    page.locator("#name_0").fill("Edited name")
    page.locator("#key_0").fill("synthetic-only")
    form.get_by_role("button", name="下一步", exact=True).click()
    expect(form.locator(".model-browser-trigger")).to_be_visible()
    form.get_by_role("button", name="下一步", exact=True).click()
    expect(page.locator('button[onclick="saveProvider(0)"]')).to_be_visible()
    form.get_by_role("button", name="1  接入配置", exact=True).click()
    assert page.locator("#name_0").input_value() == "Edited name"
    assert page.locator("#key_0").input_value() == "synthetic-only"
    page.once("dialog", lambda dialog: dialog.dismiss())
    form.get_by_label("接入预设", exact=True).select_option("google")
    assert page.locator("#url_0").input_value() == "https://example.invalid/v1"
    requests = []
    page.on("request", lambda request: requests.append(request.method))
    page.once("dialog", lambda dialog: dialog.accept())
    form.get_by_label("接入预设", exact=True).select_option("google")
    assert page.locator("#endpoint_type_0").input_value() == "gemini"
    assert page.locator("#key_0").input_value() == "synthetic-only"
    assert "POST" not in requests
    page.locator("#key_0").fill("")
    for width in (1384, 390):
        page.set_viewport_size({"width": width, "height": 920})
        box = form.bounding_box()
        assert box["width"] <= width
        assert form.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
        page.screenshot(path=str(tmp_path / f"provider-steps-{width}.png"))


def test_progress_and_notifications_follow_terminal_events(page, tmp_path):
    page.evaluate("""() => {
        document.querySelector('#pageDashboard').classList.add('hidden');
        document.querySelector('#pageDashboard').style.display = 'none';
        document.querySelector('#pageGenerate').classList.remove('hidden');
        document.querySelector('#pageGenerate').style.display = 'block';
        groupedPreviews = {};
        createPreviewPlaceholders({synthetic_0:{status:'queued', name:'Demo Image'}});
    }""")
    holder = page.locator("#prev_ph_synthetic_0 .generation-placeholder")
    expect(holder).to_be_visible()
    expect(holder).to_have_attribute("aria-busy", "true")
    page.evaluate("genboxGenerationUX.progress({synthetic_0:{status:'generating',progress:90}})")
    expect(holder).to_contain_text("生成中")
    assert holder.locator('[role="progressbar"]').get_attribute("aria-valuenow") is None
    for width in (1384, 390):
        page.set_viewport_size({"width": width, "height": 920})
        page.screenshot(path=str(tmp_path / f"generation-progress-{width}.png"))
    payload = {"status": "completed", "provider_states": {
        "synthetic_0": {"status": "completed"}, "synthetic_1": {"status": "failed"}},
        "results": {"synthetic_0": {"success": True}, "synthetic_1": {"success": False}},
        "error": "synthetic-secret-must-not-appear"}
    page.evaluate("(data) => {genboxGenerationUX.finish(data,'test-1');genboxGenerationUX.finish(data,'test-1');}", payload)
    expect(page.locator(".generation-notice")).to_have_count(1)
    expect(page.locator(".generation-notice")).to_contain_text("部分生成完成")
    assert "synthetic-secret" not in page.locator(".generation-notice").inner_text()
    page.evaluate("genboxGenerationUX.finish({status:'cancelled'},'test-2')")
    expect(holder).to_have_attribute("aria-busy", "false")
    expect(holder).to_contain_text("已取消")
    page.evaluate("genboxGenerationUX.finish({status:'failed', error:'private'},'test-3')")
    expect(page.locator(".generation-notice.error")).to_have_attribute("role", "alert")
    page.locator(".generation-notice.error button").click()
    expect(page.locator(".generation-notice.error")).to_have_count(0)
    page.evaluate("genboxGenerationUX.finish({status:'completed',results:{a:{success:true}}},'test-4')")
    expect(page.locator(".generation-notice.success")).to_be_visible()
    stack = page.locator("#generationNotifications").bounding_box()
    assert stack["x"] >= 0 and stack["x"] + stack["width"] <= 390
    page.screenshot(path=str(tmp_path / "generation-notifications.png"))
    page.emulate_media(reduced_motion="reduce")
    assert holder.locator(".generation-placeholder-track span").evaluate(
        "el => getComputedStyle(el).animationName") == "none"


def show_provider_form(page):
    page.evaluate("""() => {
        document.getElementById('providerModal').classList.add('show');
        document.getElementById('providerModal').style.display = 'flex';
        renderProviderEdit();
    }""")
    page.locator(".provider-steps button").nth(1).click()


@pytest.mark.parametrize("success", [True, False])
def test_fetch_models_keeps_step_and_drafts(page, success):
    provider = page.evaluate("allProviders[0]")
    provider["models"] = ["gemini-3.1-flash-image", "gemini-2.5-flash"]
    page.route("**/api/providers", lambda route: route.fulfill(
        json={"providers": [provider]} if route.request.method == "GET" else {"success": True}))
    page.route("**/api/providers/fetch-models-preview", lambda route: route.fulfill(json={
        "success": success, "count": 2, "models": ["gemini-3.1-flash-image", "gemini-2.5-flash"],
        "detail": "Synthetic fetch failed",
    }))
    show_provider_form(page)
    page.evaluate("document.getElementById('name_0').value = 'Draft name'")
    page.locator("#fetchBtn_0").click()
    expect(page.locator("#fetchStatus_0")).to_contain_text("2" if success else "Synthetic fetch failed")
    expect(page.locator("#fetchBtn_0")).to_be_enabled()
    expect(page.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    expect(page.locator(".model-browser-trigger").first).to_be_visible()
    assert page.locator("#name_0").input_value() == "Draft name"
    if success:
        assert "gemini-3.1-flash-image" in page.locator("#model_0 option").evaluate_all(
            "els => els.map(el => el.value)")
        page.locator(".provider-guided-form .model-browser-trigger").click()
        expect(page.locator(".model-browser-dialog")).to_contain_text("Nano Banana 2")
        page.keyboard.press("Escape")
    page.evaluate("renderProviderEdit()")
    expect(page.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    page.evaluate("""() => {
        allProviders.unshift({id:'another', name:'Another', type:'image', models:[], model:''});
        providerEditOpenIdx = 1; renderProviderEdit();
    }""")
    expect(page.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    page.evaluate("providerEditOpenIdx = 0; renderProviderEdit()")
    expect(page.locator(".provider-steps button").nth(0)).to_have_attribute("aria-current", "step")


MODELS = [
    "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-lite-image", "gemini-3.1-flash-image",
    "gemini-3-pro-image", "gemini-3-pro-image-preview", "gemini-2.5-flash-image",
    "gemini-embedding-001", "veo-3.0-generate", "lyria-3",
    "gpt-image-2.5-c", "Nano-Banana-2", "flux-dev", "custom-image",
]


def setup_catalog(page):
    page.evaluate("""models => {
        allProviders[0].models = models;
        allProviders[0].model = 'gemini-2.5-flash';
        allProviders[0].capabilities = {t2i:true, i2i:true};
        allProviders[0].model_capabilities = {'custom-image':{image_generation:false}};
    }""", MODELS)


def test_model_browser_search_categories_groups_and_raw_values(page, tmp_path):
    setup_catalog(page)
    show_provider_form(page)
    requests = []
    page.on("request", lambda request: requests.append(request.method))
    trigger = page.locator(".provider-guided-form .model-browser-trigger")
    trigger.click()
    dialog = page.locator(".model-browser-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.locator(".model-browser-row")).to_have_count(len(MODELS))
    dialog.locator('[data-category="image"]').click()
    expect(dialog.locator(".model-browser-row")).to_have_count(8)
    expect(dialog.locator('[data-model="gemini-2.5-flash"]')).to_have_count(0)
    search = dialog.get_by_role("searchbox")
    search.fill("nano banana")
    expect(dialog.locator(".model-browser-row")).to_have_count(6)
    expect(dialog.locator("summary")).to_contain_text(["Nano Banana"])
    search.fill("no match")
    expect(dialog.get_by_role("status")).to_have_text("没有匹配的模型")
    assert page.locator("#model_0").input_value() == "gemini-2.5-flash"
    search.fill("")
    summary = dialog.locator("summary").filter(has_text="Nano Banana")
    summary.click()
    expect(dialog.locator('[data-model="gemini-3.1-flash-image"]')).not_to_be_visible()
    summary.click()
    for width in (1384, 390):
        page.set_viewport_size({"width": width, "height": 920})
        box = dialog.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
        assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
        page.screenshot(path=str(tmp_path / f"model-browser-{width}.png"))
    dialog.locator('[data-model="gemini-3.1-flash-image"]').click()
    expect(dialog).to_have_count(0)
    assert page.locator("#model_0").input_value() == "gemini-3.1-flash-image"
    expect(trigger).to_contain_text("Nano Banana 2")
    trigger.click()
    expect(page.locator('.model-browser-row[data-model="gemini-3.1-flash-image"]')).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Escape")
    expect(trigger).to_be_focused()
    assert "POST" not in requests


@pytest.mark.parametrize("mode", ["t2i", "i2i"])
def test_generation_uses_eligible_models_and_keeps_provider_isolation(page, mode):
    setup_catalog(page)
    page.evaluate("""mode => {
        currentMode = mode;
        allProviders.push({...allProviders[0], id:'other', name:'Other endpoint',
            model_capabilities:{'gemini-3.1-flash-image':{t2i:false,i2i:false}}});
        selectedProviders = ['synthetic', 'other'];
        document.getElementById('pageDashboard').style.display = 'none';
        document.getElementById('pageGenerate').classList.remove('hidden');
        document.getElementById('pageGenerate').style.display = 'block';
        renderProviderList(); loadModelDropdown();
    }""", mode)
    values = page.locator('select[data-generation-provider="synthetic"] option').evaluate_all("els => els.map(el => el.value)")
    assert "gemini-3.1-flash-image" in values
    assert "Nano-Banana-2" in values
    assert not set(values) & {"gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview-tts",
                              "veo-3.0-generate", "gemini-embedding-001", "lyria-3", "custom-image"}
    other_values = page.locator('select[data-generation-provider="other"] option').evaluate_all("els => els.map(el => el.value)")
    assert "gemini-3.1-flash-image" not in other_values
    trigger = page.locator("#providerList .model-browser-trigger").first
    trigger.click()
    dialog = page.locator(".model-browser-dialog")
    dialog.get_by_role("searchbox").fill("Nano-Banana-2")
    dialog.locator('[data-model="Nano-Banana-2"]').click()
    settings = page.evaluate("generationProviderModelSettings(selectedProviders, '_global')")
    assert settings["synthetic"]["model"] == "Nano-Banana-2"
    assert page.evaluate("generationProviderModelSettings(selectedProviders, 'gemini-3.1-flash-image')") == settings
    assert settings["other"]["model"] != "gemini-3.1-flash-image"
    trigger.click()
    dialog.get_by_role("searchbox").fill("absent")
    page.keyboard.press("Escape")
    assert page.evaluate("generationProviderModelSettings(selectedProviders, '_global')") == settings
    assert page.evaluate("allProviders[0].model") == "gemini-2.5-flash"


VIDEO_MODELS = [
    "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview",
    "veo-3.1-lite-generate-preview", "gemini-omni-flash-preview",
    "gemini-omni-1.1-flash",
]


def setup_video_catalog(page):
    page.evaluate("""models => {
        allProviders[0].type = 'video';
        allProviders[0].models = models;
        allProviders[0].model = models[1];
        videoProviders = [allProviders[0]];
        selectedVideoProviderIds = ['synthetic'];
        currentVideoMode = 'ti2vid';
        document.getElementById('pageDashboard').style.display = 'none';
        document.getElementById('pageVideo').classList.remove('hidden');
        document.getElementById('pageVideo').style.display = 'block';
        renderVideoProviderCards();
    }""", VIDEO_MODELS + ["gemini-2.5-flash", "gemini-3.1-flash-image"])


def test_video_models_survive_mode_filter_and_empty_does_not_show_text(page):
    setup_video_catalog(page)
    select = page.locator("#vmodel_synthetic")
    assert select.locator("option").evaluate_all("els => els.map(el => el.value)") == VIDEO_MODELS
    assert select.input_value() == VIDEO_MODELS[1]
    page.evaluate("currentVideoMode = 'i2vid'; renderVideoProviderCards()")
    assert select.input_value() == VIDEO_MODELS[1]
    assert select.locator("option").evaluate_all("els => els.map(el => el.value)") == VIDEO_MODELS
    page.evaluate("currentVideoMode = 'keyframes'; renderVideoProviderCards()")
    assert select.input_value() == ""
    expect(page.locator("#videoGenBtn")).to_be_disabled()


@pytest.mark.parametrize("success", [True, False])
def test_video_refresh_uses_authenticated_backend_without_models_url(page, success):
    setup_video_catalog(page)
    page.route("**/api/providers/fetch-models/synthetic", lambda route: route.fulfill(json={
        "success": success, "models": [VIDEO_MODELS[0]], "detail": "Synthetic denied",
    }))
    page.evaluate("refreshProviderModels('synthetic')")
    select = page.locator("#vmodel_synthetic")
    if success:
        assert select.locator("option").evaluate_all("els => els.map(el => el.value)") == [VIDEO_MODELS[0]]
    else:
        assert select.locator("option").count() == len(VIDEO_MODELS)
        expect(page.locator('#vcard_synthetic button[onclick*="refresh"]')).to_be_enabled()
        expect(page.locator("#statusLeft")).to_contain_text("Synthetic denied")


def test_provider_video_catalog_classifies_omni_without_resetting_fetch_step(page):
    setup_video_catalog(page)
    show_provider_form(page)
    page.route("**/api/providers", lambda route: route.fulfill(
        json={"providers": page_provider} if route.request.method == "GET" else {"success": True}))
    page_provider = page.evaluate("allProviders")
    page.route("**/api/providers/fetch-models-preview", lambda route: route.fulfill(json={
        "success": True, "models": page_provider[0]["models"], "count": len(page_provider[0]["models"]),
    }))
    page.locator("#fetchBtn_0").click()
    expect(page.locator("#fetchBtn_0")).to_be_enabled()
    expect(page.locator("#fetchStatus_0")).to_contain_text(str(len(page_provider[0]["models"])))
    expect(page.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    page.locator(".provider-guided-form .model-browser-trigger").click()
    dialog = page.locator(".model-browser-dialog")
    dialog.locator('[data-category="video"]').click()
    for model in VIDEO_MODELS:
        expect(dialog.locator(f'[data-model="{model}"]')).to_be_visible()
    expect(dialog.locator('[data-model="gemini-2.5-flash"]')).to_have_count(0)


@pytest.mark.parametrize("kind", ["video", "image"])
def test_new_provider_fetches_before_save_with_no_id_and_saves_once(page, kind):
    previews, saves = [], []
    models = VIDEO_MODELS[:2] if kind == "video" else ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
    page.evaluate("""kind => {
        allProviders = [{id:'', name:'New', type:kind, model:'', models:[],
            enabled:true, api_key:'', api_keys:[], base_url:'', endpoint_type:'gemini'}];
        providerEditOpenIdx = 0;
        document.getElementById('providerModal').style.display = 'flex';
        document.getElementById('providerModal').classList.add('show');
        renderProviderEdit();
    }""", kind)

    def preview(route):
        previews.append(route.request.post_data_json)
        route.fulfill(json={"success": True, "models": models, "count": len(models)})

    def persist(route):
        if route.request.method == "POST":
            saves.append(route.request.post_data_json)
            route.fulfill(json={"ok": True})
        else:
            route.fulfill(json={"providers": [{**saves[-1], "api_key": "", "has_key": True}]})

    page.route("**/api/providers/fetch-models-preview", preview)
    page.route("**/api/providers", persist)
    page.locator("#name_0").fill("Draft endpoint")
    page.locator("#url_0").fill("https://generativelanguage.googleapis.com")
    page.locator("#key_0").fill("synthetic-new-draft-key")
    form = page.locator(".provider-guided-form")
    form.get_by_role("button", name="下一步", exact=True).click()
    assert not saves and not previews
    page.locator("#fetchBtn_0").click()
    expect(page.locator("#fetchStatus_0")).to_contain_text("2")
    expect(page.locator("#fetchBtn_0")).to_be_enabled()
    assert len(previews) == 1 and not saves
    assert previews[0]["id"] == ""
    assert previews[0]["api_key"] == "synthetic-new-draft-key"
    assert previews[0]["base_url"] == "https://generativelanguage.googleapis.com"
    expect(form.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    assert page.evaluate("allProviders[0].id") == ""
    assert page.evaluate("allProviders[0].models") == []
    assert page.locator("#key_0").input_value() == "synthetic-new-draft-key"
    assert "synthetic-new-draft-key" not in page.evaluate("JSON.stringify(localStorage) + JSON.stringify(sessionStorage)")
    form.locator(".model-browser-trigger").click()
    page.locator(f'.model-browser-dialog [data-model="{models[1]}"]').click()
    form.get_by_role("button", name="下一步", exact=True).click()
    page.locator('button[onclick="saveProvider(0)"]').click()
    expect(page.locator("#statusLeft")).to_contain_text("Draft endpoint")
    assert len(saves) == 1
    assert saves[0]["id"].startswith("p_")
    assert saves[0]["id"] != "tmp"
    assert saves[0]["model"] == models[1]
    assert saves[0]["models"] == models
    assert saves[0]["api_key"] == "synthetic-new-draft-key"


def test_unsaved_preview_failure_keeps_draft_and_can_retry(page):
    page.evaluate("""() => {
        allProviders[0].id = ''; allProviders[0].has_key = false;
    }""")
    show_provider_form(page)
    page.evaluate("document.getElementById('key_0').value = 'synthetic-failed-key'")
    requests = []

    def preview(route):
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            route.fulfill(status=503, json={"detail": "Temporary failure"})
        else:
            route.fulfill(json={"success": True, "models": ["demo-image"], "count": 1})

    page.route("**/api/providers/fetch-models-preview", preview)
    page.locator("#fetchBtn_0").click()
    expect(page.locator("#fetchStatus_0")).to_contain_text("HTTP 503")
    expect(page.locator("#fetchBtn_0")).to_be_enabled()
    expect(page.locator(".provider-steps button").nth(1)).to_have_attribute("aria-current", "step")
    assert page.locator("#key_0").input_value() == "synthetic-failed-key"
    page.locator("#fetchBtn_0").click()
    expect(page.locator("#fetchStatus_0")).to_contain_text("1")
    assert len(requests) == 2
    assert page.evaluate("allProviders[0].id") == ""
