"""Video input visibility and layout with synthetic local files only."""

import base64

import pytest
from playwright.sync_api import expect

from test_generation_experience_browser import page, setup_video_catalog


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aC1sAAAAASUVORK5CYII="
)


def show_video(page, mode="i2vid", workbench="multi"):
    setup_video_catalog(page)
    page.evaluate("""([mode, workbench]) => {
        document.querySelectorAll('.page-content').forEach(el => {
            el.style.removeProperty('display');
            el.classList.toggle('hidden', el.id !== 'pageVideo');
        });
        setCreatorWorkbenchMode('video', workbench);
        switchVideoSubTab(mode);
    }""", [mode, workbench])


@pytest.mark.parametrize("workbench", ["multi", "single"])
def test_video_modes_have_visible_inputs_and_local_preview(page, workbench):
    show_video(page, workbench=workbench)
    requests = []
    page.on("request", lambda request: requests.append(request))
    expect(page.locator("#videoI2VPanel")).to_be_visible()
    expect(page.locator("#videoKeyframesPanel")).not_to_be_visible()
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name="上传参考图片", exact=True).click()
    chooser.value.set_files({"name": "synthetic.png", "mimeType": "image/png", "buffer": PNG})
    card = page.locator("#videoImagePreview .video-image-card")
    expect(card).to_have_count(1)
    assert card.locator("img").evaluate("el => el.complete && el.naturalWidth > 0")
    page.get_by_role("button", name="预览图片 1", exact=True).click()
    expect(page.locator("#lightbox")).to_be_visible()
    page.locator('#lightbox-controls button[onclick="closeLightbox(event)"]').click()
    page.get_by_role("button", name="移除图片 1", exact=True).click()
    expect(card).to_have_count(0)
    page.locator("#videoFileInput").set_input_files(
        {"name": "synthetic.png", "mimeType": "image/png", "buffer": PNG})
    expect(card).to_have_count(1)
    page.locator("#vSubTabKeyframes").click()
    expect(page.locator("#videoI2VPanel")).not_to_be_visible()
    expect(page.locator("#videoKeyframesPanel")).to_be_visible()
    assert page.evaluate("videoImages.length") == 0
    page.locator("#kfFileInput").set_input_files([
        {"name": "frame1.png", "mimeType": "image/png", "buffer": PNG},
        {"name": "frame2.png", "mimeType": "image/png", "buffer": PNG},
    ])
    expect(page.locator("#kfImagePreview .video-image-card")).to_have_count(2)
    page.locator("#vSubTabTi2vid").click()
    expect(page.locator("#videoKeyframesPanel")).not_to_be_visible()
    assert page.evaluate("kfImages.length") == 0
    assert not [request for request in requests if request.method == "POST"]
    assert not [request for request in requests if "mockapi.io" in request.url]


@pytest.mark.parametrize("workbench", ["multi", "single"])
@pytest.mark.parametrize("mode", ["ti2vid", "i2vid", "keyframes"])
@pytest.mark.parametrize("width,height", [(1384, 920), (1024, 700), (390, 844)])
def test_video_composer_controls_stay_inside_bounds(page, tmp_path, workbench, mode, width, height):
    page.set_viewport_size({"width": width, "height": height})
    show_video(page, mode, workbench)
    composer = page.locator(".video-composer")
    button = page.locator("#videoGenBtn")
    button.scroll_into_view_if_needed()
    expect(button).to_be_in_viewport()
    measurements = page.evaluate("""() => {
        const box = el => {
            const r = el.getBoundingClientRect();
            return {left:r.left, top:r.top, right:r.right, bottom:r.bottom};
        };
        const composer = document.querySelector('.video-composer');
        return {
            composer:box(composer), button:box(document.getElementById('videoGenBtn')),
            prompt:box(document.getElementById('videoPrompt')),
            overflow:composer.scrollWidth > composer.clientWidth + 1
        };
    }""")
    assert not measurements["overflow"]
    for name in ("button", "prompt"):
        control = measurements[name]
        outer = measurements["composer"]
        assert outer["left"] <= control["left"] < control["right"] <= outer["right"] + 1
        assert outer["top"] <= control["top"] < control["bottom"] <= outer["bottom"] + 1
    assert measurements["composer"]["right"] <= width + 1
    page.screenshot(path=str(tmp_path / f"video-{mode}-{workbench}-{width}.png"))


def test_video_drop_and_invalid_files_do_not_upload_to_network(page):
    show_video(page)
    page.locator("#videoI2VPanel .video-upload-list").evaluate("""(el, bytes) => {
        const transfer = new DataTransfer();
        transfer.items.add(new File([new Uint8Array(bytes)], 'drop.png', {type:'image/png'}));
        el.dispatchEvent(new DragEvent('drop', {bubbles:true, dataTransfer:transfer}));
    }""", list(PNG))
    expect(page.locator("#videoImagePreview .video-image-card")).to_have_count(1)
    page.locator("#videoFileInput").set_input_files(
        {"name": "not-image.txt", "mimeType": "text/plain", "buffer": b"synthetic"})
    expect(page.locator("#statusLeft")).to_contain_text("请选择图片文件")
    expect(page.locator("#videoImagePreview .video-image-card")).to_have_count(1)
    page.evaluate("""() => readVideoImageFile(
        new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'large.png', {type:'image/png'})
    )""")
    expect(page.locator("#statusLeft")).to_contain_text("10MB")


def test_provider_group_titles_strip_whole_unicode_emoji(page):
    page.evaluate("renderProviderEdit()")
    titles = page.locator("#providerGrid .provider-group-icon + span").all_text_contents()
    assert titles == ["生图模型", "生视频模型", "提示词优化"]
    expect(page.locator("#providerGrid .provider-type-card > div > div > .provider-group-icon svg")).to_have_count(3)


def test_video_advanced_opens_on_first_click_and_closes(page):
    show_video(page, mode="ti2vid")
    expect(page.locator("#videoAdvanced")).not_to_be_visible()
    toggle = page.locator('[onclick="toggleVideoAdvanced()"]')
    toggle.click()
    for selector in ("#videoSteps", "#videoSeed", "#videoNegPrompt"):
        expect(page.locator(selector)).to_be_visible()
    toggle.click()
    expect(page.locator("#videoAdvanced")).not_to_be_visible()
    toggle.click()
    expect(page.locator("#videoSeed")).to_be_visible()


@pytest.mark.parametrize("width", [1384, 390])
def test_video_submission_failure_is_visible_and_retryable(page, tmp_path, width):
    page.set_viewport_size({"width": width, "height": 920})
    show_video(page)
    page.locator("#videoFileInput").set_input_files(
        {"name": "synthetic.png", "mimeType": "image/png", "buffer": PNG})
    page.locator("#videoPrompt").fill("Synthetic motion")
    detail = "Google 官方视频生成接口尚未接入；本次未向上游发送生成请求。"
    submissions = []

    def reject(route):
        submissions.append(route.request.post_data_json)
        route.fulfill(status=501, json={"detail": detail})

    page.route("**/api/video/generate", reject)
    page.locator("#videoGenBtn").click()
    expect(page.locator("#videoGenBtn")).to_be_enabled()
    expect(page.locator("#videoProgressText")).to_have_text("提交失败")
    expect(page.locator("#videoLogWrap")).to_be_visible()
    expect(page.locator("#videoPerProviderSection")).to_be_visible()
    expect(page.locator("#videoLogArea")).to_contain_text(detail)
    expect(page.locator("#vprev_ph_synthetic")).to_be_visible()
    expect(page.locator("#vprev_ph_synthetic")).to_have_attribute("role", "alert")
    expect(page.locator("#vprev_ph_synthetic")).to_contain_text(detail)
    page.locator("#vprev_ph_synthetic .ph-text").scroll_into_view_if_needed()
    expect(page.locator("#vprev_ph_synthetic .ph-text")).to_be_in_viewport()
    expect(page.locator("#vprev_ph_synthetic .spinner")).to_have_count(0)
    assert page.evaluate("videoElapsedTimer") is None
    assert page.evaluate("videoPollTimer") is None
    assert len(submissions) == 1
    assert submissions[0]["mode"] == "i2vid"
    assert len(submissions[0]["image"]) == 1
    assert page.evaluate("""() => {
        const body = document.querySelector('.video-composer-body').getBoundingClientRect();
        const button = document.getElementById('videoGenBtn').getBoundingClientRect();
        const status = document.querySelector('#videoFeedbackSlot').getBoundingClientRect();
        const composer = document.querySelector('.video-composer').getBoundingClientRect();
        return body.bottom <= button.top + 1 && status.bottom <= composer.top + 1;
    }""")
    page.screenshot(path=str(tmp_path / f"video-submit-failure-{width}.png"))
    page.evaluate("clearVideoLog()")
    expect(page.locator("#videoLogWrap")).not_to_be_visible()
    page.locator("#videoGenBtn").click()
    expect(page.locator("#videoLogWrap")).to_be_visible()
    expect(page.locator("#videoProgressText")).to_have_text("提交失败")
    assert len(submissions) == 2


@pytest.mark.parametrize("failed_provider", ["synthetic", "second", "both"])
def test_video_submission_continues_after_a_provider_failure(page, failed_provider):
    show_video(page, mode="ti2vid")
    page.evaluate("""() => {
        videoProviders.push({...videoProviders[0], id:'second', name:'Second'});
        selectedVideoProviderIds = ['synthetic', 'second'];
        renderVideoProviderCards();
        window.polledTasks = null;
        startVideoPolling = tasks => {window.polledTasks = tasks; stopVideoElapsedTimer();};
    }""")
    submissions = []

    def submit(route):
        provider_id = route.request.post_data_json["provider_id"]
        submissions.append(provider_id)
        if failed_provider in (provider_id, "both"):
            route.fulfill(status=501, json={"detail": "Synthetic unsupported endpoint"})
        else:
            route.fulfill(json={"task_id": "synthetic-task-123", "status": "pending"})

    page.route("**/api/video/generate", submit)
    page.locator("#videoPrompt").fill("Synthetic motion")
    page.locator("#videoGenBtn").click()
    page.wait_for_function("""() =>
        window.polledTasks !== null || document.getElementById('videoProgressText').textContent === '提交失败'
    """)
    assert submissions == ["synthetic", "second"]
    if failed_provider == "both":
        assert page.evaluate("window.polledTasks") is None
        expect(page.locator("#videoGenBtn")).to_be_enabled()
    else:
        tasks = page.evaluate("window.polledTasks")
        assert len(tasks) == 1
        assert tasks[0]["provider_id"] != failed_provider
    expect(page.locator("#videoLogArea")).to_contain_text("Synthetic unsupported endpoint")


def test_video_advanced_explains_unsupported_parameters(page):
    show_video(page, mode="ti2vid")
    page.evaluate("""async () => {
        _videoModelSpecCache['synthetic-no-advanced'] = {
            supports_seed:false, supports_negative_prompt:false
        };
        await updateVideoUIByModelSpec('synthetic-no-advanced');
    }""")
    page.locator('[onclick="toggleVideoAdvanced()"]').click()
    expect(page.locator("#videoAdvancedEmpty")).to_be_visible()
    for selector in ("#videoSteps", "#videoSeed", "#videoNegPrompt"):
        expect(page.locator(selector)).not_to_be_visible()
    page.evaluate("""async () => {
        _videoModelSpecCache['synthetic-seed'] = {supports_seed:true};
        await updateVideoUIByModelSpec('synthetic-seed');
    }""")
    expect(page.locator("#videoAdvancedEmpty")).not_to_be_visible()
    expect(page.locator("#videoSeed")).to_be_visible()
