"""Google-native video controls with synthetic backend contracts."""

import re

import pytest
from playwright.sync_api import expect

from test_generation_experience_browser import page
from test_video_composer_browser import show_video, PNG
from providers.google_video import model_spec


def native(page, model="veo-3.1-fast-generate-preview"):
    page.route("**/api/video/model-spec/**", lambda route: route.fulfill(
        json={"spec": model_spec(route.request.url.split("/model-spec/")[1].split("?")[0])}))
    show_video(page, "i2vid")
    page.evaluate("""model => {
        videoProviders[0].base_url = 'https://generativelanguage.googleapis.com/v1beta';
        videoProviders[0].models = [model];
        videoProviders[0].model = model;
        renderVideoProviderCards();
    }""", model)
    expect(page.locator("#videoNativeOptions")).to_be_visible()


def test_veo_duration_resolution_and_payload_are_native(page):
    native(page)
    expect(page.locator("#videoFramesRow")).not_to_be_visible()
    expect(page.locator("#videoFPS")).not_to_be_visible()
    assert page.locator("#videoNativeDuration option").all_text_contents() == ["4", "6", "8"]
    page.locator("#videoNativeResolution").select_option("1080p")
    assert page.locator("#videoNativeDuration option").all_text_contents() == ["8"]
    page.locator("#videoNativeAspect").select_option("9:16")
    page.locator("#videoFileInput").set_input_files(
        {"name": "synthetic.png", "mimeType": "image/png", "buffer": PNG})
    page.locator("#videoPrompt").fill("Synthetic scene")
    page.route("**/api/video/generate", lambda route: route.fulfill(status=403, json={"detail": "Synthetic quota"}))
    with page.expect_request("**/api/video/generate") as req:
        page.locator("#videoGenBtn").click()
    payload = req.value.post_data_json
    assert payload["duration_seconds"] == 8
    assert payload["frame_rate"] == 24
    assert payload["resolution"] == "1080p"
    assert payload["aspect_ratio"] == "9:16"
    assert (payload["width"], payload["height"]) == (1080, 1920)
    assert payload["num_inference_steps"] is None
    assert payload["negative_prompt"] is None
    assert len(payload["image"]) == 1


def test_omni_does_not_expose_agnes_parameters(page):
    native(page, "gemini-omni-1.1-flash")
    expect(page.locator("#videoNativeDurationField")).not_to_be_visible()
    expect(page.locator("#videoNativeAutoDuration")).to_contain_text("3–10")
    assert page.locator("#videoNativeResolution option").all_text_contents() == ["360p", "720p", "1080p", "4k"]
    page.locator('[onclick="toggleVideoAdvanced()"]').click()
    expect(page.locator("#videoSteps")).not_to_be_visible()
    expect(page.locator("#videoSeed")).not_to_be_visible()
    expect(page.locator("#videoAdvancedEmpty")).to_be_visible()


def test_native_last_frame_explains_capability_without_enabling_it(page):
    native(page, "gemini-omni-1.1-flash")
    last_frame = page.locator('input[name="videoImageRole"][value="last_frame"]')
    expect(last_frame).to_be_disabled()
    expect(page.locator("#videoImageRoleHint")).to_contain_text("单独尾帧不可用")
    expect(last_frame.locator("..")).to_have_attribute("title", re.compile("当前模型未开放单独尾帧"))
    page.locator('input[name="videoImageRole"][value="first_last"]').locator("..").click()
    page.locator("#videoFileInput").set_input_files([
        {"name": f"frame{i}.png", "mimeType": "image/png", "buffer": PNG} for i in range(2)
    ])
    expect(page.locator("#videoImagePreview .video-image-label")).to_have_text(["首帧", "尾帧"])


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width", [1494, 1024, 390])
def test_video_role_capsules_remain_legible_and_inside_asset_panel(page, tmp_path, theme, width):
    page.set_viewport_size({"width": width, "height": 994 if width != 1024 else 700})
    native(page, "gemini-omni-1.1-flash")
    page.evaluate("theme => applyTheme(theme === 'dark' ? 'graphite' : 'apple-mono')", theme)
    role = page.locator('label.video-image-role-option:has(input[value="reference"])')
    role.click()
    expect(role.locator("span")).to_have_css("color", "rgb(255, 255, 255)")
    panel = page.locator("#videoI2VPanel")
    assert panel.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    assert page.evaluate("""() => {
        const panel = document.querySelector('#videoI2VPanel').getBoundingClientRect();
        return [...document.querySelectorAll('.video-image-role-option, #videoImageRoleHint')]
            .every(el => {
                const r = el.getBoundingClientRect();
                return r.top >= panel.top && r.bottom <= panel.bottom + 1;
            });
    }""")
    panel.screenshot(path=str(tmp_path / f"video-role-capsules-{theme}-{width}.png"))


def test_model_change_refreshes_parameters_without_stale_480p(page):
    native(page, "gemini-omni-1.1-flash")
    page.evaluate("""() => {
        videoProviders[0].models.push('veo-3.1-fast-generate-preview');
        renderVideoProviderCards();
    }""")
    page.locator("#vmodel_synthetic").select_option("veo-3.1-fast-generate-preview")
    expect(page.locator("#videoNativeDurationField")).to_be_visible()
    assert page.locator("#videoNativeResolution option").all_text_contents() == ["720p", "1080p", "4k"]


def test_feedback_is_above_prompt_at_reported_viewport(page, tmp_path):
    page.set_viewport_size({"width": 1114, "height": 994})
    native(page)
    page.evaluate("""() => {
        videoLog('Synthetic task waiting', 'info');
        renderVideoPerProviderBars();
    }""")
    feedback = page.locator("#videoFeedbackSlot")
    expect(feedback).to_be_visible()
    assert page.evaluate("""() =>
        document.getElementById('videoFeedbackSlot').getBoundingClientRect().bottom <=
        document.querySelector('.video-composer').getBoundingClientRect().top + 1
    """)
    page.screenshot(path=str(tmp_path / "native-video-feedback.png"))


def test_native_async_failure_stays_failed_and_shows_reason(page):
    native(page)
    page.route("**/api/video/status/native-test", lambda route: route.fulfill(json={
        "task_id": "native-test", "provider_id": "synthetic", "provider_type": "google_native",
        "status": "failed", "error": "Google 视频接口返回 HTTP 429", "elapsed_seconds": 1,
    }))
    page.evaluate("""() => {
        const original = window.setInterval;
        window.setInterval = (fn, ms) => original(fn, ms === 5000 ? 100 : ms);
        createVideoPreviewPlaceholders([{provider_id:'synthetic', model:'veo-3.1-fast-generate-preview'}]);
        renderVideoPerProviderBars();
        startVideoPolling([{task_id:'native-test',provider_id:'synthetic',status:'queued'}]);
    }""")
    expect(page.locator("#videoProgressText")).to_contain_text("1 项失败")
    expect(page.locator("#videoPreviewResults [role=alert]")).to_contain_text("HTTP 429")
    expect(page.locator("#videoGenBtn")).to_be_enabled()
    expect(page.locator("#statusLeft")).to_contain_text("0 项成功，1 项失败")


def test_native_async_completion_uses_local_authenticated_video(page):
    native(page)
    page.route("**/api/video/status/native-test", lambda route: route.fulfill(json={
        "task_id": "native-test", "provider_id": "synthetic", "provider_type": "google_native",
        "status": "completed", "video_url_local": "/api/video/file/synthetic.mp4",
        "elapsed_seconds": 1, "progress": 100,
    }))
    page.evaluate("""() => {
        const original = window.setInterval;
        window.setInterval = (fn, ms) => original(fn, ms === 5000 ? 100 : ms);
        createVideoPreviewPlaceholders([{provider_id:'synthetic', model:'veo-3.1-fast-generate-preview'}]);
        renderVideoPerProviderBars();
        startVideoPolling([{task_id:'native-test',provider_id:'synthetic',status:'queued'}]);
    }""")
    expect(page.locator("#videoPreviewResults video")).to_have_attribute("src", "/api/video/file/synthetic.mp4")
    expect(page.locator("#statusLeft")).to_contain_text("1 项成功，0 项失败")
