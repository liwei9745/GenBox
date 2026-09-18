"""Video input visibility and layout with synthetic local files only."""

import base64
import re

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


@pytest.mark.parametrize("workbench", ["multi", "single"])
def test_video_layout_drag_prompt_growth_and_full_width(page, tmp_path, workbench):
    show_video(page, workbench=workbench)
    prompt = page.locator("#videoPrompt")
    preview = page.locator("#videoPreviewPanel")
    handle = page.locator(".video-preview-frame .resize-handle-bottom")
    expect(handle).to_be_visible()
    prompt.fill("Short prompt")
    short = prompt.bounding_box()["height"]
    prompt.fill("\n".join(["Synthetic long prompt"] * 80))
    expect(prompt).to_have_css("height", "160px")
    assert prompt.bounding_box()["height"] > short
    assert prompt.evaluate("el => el.scrollHeight > el.clientHeight")
    before = preview.bounding_box()["height"]
    box = handle.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] - 70, steps=8)
    page.mouse.up()
    assert preview.bounding_box()["height"] < before - 40
    manual = prompt.bounding_box()["height"]
    prompt.fill("Still keep my manual size")
    assert abs(prompt.bounding_box()["height"] - manual) <= 1
    handle.dblclick()
    expect(prompt).to_have_css("height", "88px")
    if workbench == "multi":
        sidebar = page.locator("#pageVideo .generate-left").bounding_box()
        composer = page.locator(".video-composer").bounding_box()
        assert abs(sidebar["x"] - composer["x"]) <= 1
        assert composer["width"] > preview.bounding_box()["width"] + 150
        side_handle = page.locator(".video-preview-frame .resize-handle-left")
        side_handle.focus()
        side_handle.press("ArrowRight")
        assert page.locator("#pageVideo .generate-left").bounding_box()["width"] > sidebar["width"]
    assert preview.bounding_box()["height"] >= 220
    page.screenshot(path=str(tmp_path / f"video-layout-{workbench}.png"))


def test_video_native_prompt_resize_and_long_feedback(page, tmp_path):
    show_video(page)
    prompt = page.locator("#videoPrompt")
    prompt.fill("Native resize")
    box = prompt.bounding_box()
    page.mouse.move(box["x"] + box["width"] - 4, box["y"] + box["height"] - 4)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] - 4, box["y"] + box["height"] + 70, steps=8)
    page.mouse.up()
    assert prompt.bounding_box()["height"] > box["height"] + 35
    resized = prompt.bounding_box()["height"]
    prompt.fill("Native resize retained")
    assert abs(prompt.bounding_box()["height"] - resized) <= 1
    page.evaluate("""() => {
        document.getElementById('videoLogWrap').classList.remove('hidden');
        document.getElementById('videoLogArea').textContent = 'Synthetic log\\n'.repeat(100);
    }""")
    feedback = page.locator("#videoFeedbackSlot").bounding_box()
    preview = page.locator("#videoPreviewPanel").bounding_box()
    composer = page.locator(".video-composer").bounding_box()
    # Logs now live in the preview's independent side panel. The panel should
    # fill the preview height and scroll its contents instead of consuming the
    # prompt composer or being clipped to the old inline status height.
    preview_content = page.locator("#videoPreviewPanel .video-preview-content").bounding_box()
    assert feedback["height"] >= preview_content["height"] - 2
    assert feedback["y"] >= preview_content["y"]
    assert feedback["y"] + feedback["height"] <= preview_content["y"] + preview_content["height"] + 1
    assert feedback["y"] + feedback["height"] <= preview["y"] + preview["height"] + 1
    assert feedback["y"] + feedback["height"] <= composer["y"] + composer["height"]
    expect(page.locator("#videoFeedbackSlot #videoLogArea")).to_be_visible()
    assert page.locator("#videoFeedbackSlot #videoLogArea").evaluate(
        "el => el.scrollHeight > el.clientHeight"
    )
    assert page.locator("#videoPreviewPanel").bounding_box()["height"] >= 220
    page.screenshot(path=str(tmp_path / "video-layout-feedback.png"))


def test_video_prompt_tools_preserve_data_and_require_search_intent(page, tmp_path):
    show_video(page, mode="ti2vid")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    prompt = page.locator("#videoPrompt")
    prompt.fill("Private draft stays local")
    page.get_by_role("button", name="快速提示词", exact=True).click()
    page.locator(".video-quick-options button").first.click()
    assert prompt.input_value().startswith("Private draft stays local\n")
    page.get_by_role("button", name="上传附件", exact=True).click()
    expect(page.locator("#videoI2VPanel")).to_be_visible()
    page.locator("#videoFileInput").set_input_files(
        {"name": "synthetic.png", "mimeType": "image/png", "buffer": PNG})
    expect(page.locator("#videoImagePreview .video-image-card")).to_have_count(1)
    page.evaluate("() => { window.searchCalls = []; window.open = (...args) => { searchCalls.push(args); return null; }; }")
    page.get_by_role("button", name="网络搜索", exact=True).click()
    expect(page.locator("#videoSearchQuery")).to_have_value("")
    assert page.evaluate("searchCalls.length") == 0
    page.locator("#videoSearchQuery").fill("camera motion")
    page.locator(".video-tools-dialog").get_by_role("button", name="搜索", exact=True).click()
    assert page.evaluate("searchCalls[0][0]") == "https://www.bing.com/search?q=camera%20motion"
    page.get_by_role("button", name="新会话", exact=True).click()
    page.locator(".video-tools-dialog").get_by_role("button", name="取消", exact=True).click()
    assert prompt.input_value().startswith("Private draft")
    page.get_by_role("button", name="新会话", exact=True).click()
    page.get_by_role("button", name="确认新会话", exact=True).click()
    expect(prompt).to_have_value("")
    expect(page.locator("#videoImagePreview .video-image-card")).to_have_count(0)
    expect(page.locator("#videoPreviewEmpty")).to_be_visible()
    assert page.evaluate("selectedVideoProviderIds.length") == 1
    assert not errors
    page.screenshot(path=str(tmp_path / "video-prompt-tools.png"))


def test_video_preview_uses_compact_cards_and_lightbox(page):
    show_video(page)
    page.evaluate("""() => {
        videoProviders = [{id:'synthetic', name:'Gemini', display_name:'Gemini', color:'#1677ff'}];
        videoPreviewGroups = {
            synthetic: [
                {provider_id:'synthetic', model:'veo-test', status:'completed',
                 video_url_local:'/api/video/file/one.mp4', prompt:'first result', elapsed_seconds:4},
                {provider_id:'synthetic', model:'veo-test', status:'failed',
                 error:'Synthetic failure', prompt:'failed result', elapsed_seconds:2}
            ]
        };
        renderVideoGroupedPreview();
    }""")
    results = page.locator("#videoPreviewResults")
    expect(results).to_be_visible()
    assert results.evaluate("el => getComputedStyle(el).display") == "grid"
    expect(results.locator(".video-result-group")).to_have_count(1)
    expect(results.locator(".video-result-card")).to_have_count(2)
    expect(results.locator(".video-result-card[role=alert]")).to_contain_text("Synthetic failure")
    expect(results.locator("video")).to_have_attribute("src", "/api/video/file/one.mp4")
    results.locator(".video-result-card").first.click()
    expect(page.locator("#lightbox")).to_be_visible()
    expect(page.locator("#lightbox-video")).to_have_attribute("src", "/api/video/file/one.mp4")
    page.locator('#lightbox-controls button[onclick="closeLightbox(event)"]').click()
    expect(page.locator("#lightbox")).not_to_be_visible()


def test_video_generating_preview_reuses_stage_placeholder_and_role_cards(page):
    show_video(page)
    page.evaluate("""() => {
        createVideoPreviewPlaceholders([{provider_id:'synthetic', model:'veo-test'}]);
    }""")
    holder = page.locator("#vprev_ph_synthetic")
    expect(holder).to_be_visible()
    expect(holder.locator(".generation-placeholder-track")).to_be_visible()
    expect(holder.locator(".generation-placeholder-label")).to_contain_text("Demo Image")
    assert holder.locator(".spinner").count() == 0
    roles = page.locator("#videoI2VPanel .video-image-role-option")
    expect(roles).to_have_count(4)
    expect(roles.nth(0)).to_have_class(re.compile(r"\bis-selected\b"))
    roles.nth(2).click()
    assert page.evaluate("videoImageRole") == "first_last"
    expect(roles.nth(2).locator("input")).to_be_checked()


@pytest.mark.parametrize("width", [1494, 1024, 390])
def test_video_roles_are_vertical_beside_inline_thumbnails(page, tmp_path, width):
    page.set_viewport_size({"width": width, "height": 994})
    show_video(page)
    roles = page.locator("#videoI2VPanel .video-image-role-option")
    roles.first.scroll_into_view_if_needed()
    boxes = [role.bounding_box() for role in roles.all()]
    for previous, current in zip(boxes, boxes[1:]):
        assert abs(previous["x"] - current["x"]) <= 1
        assert previous["y"] + previous["height"] <= current["y"]
    page.locator("#videoFileInput").set_input_files([
        {"name": f"frame{i}.png", "mimeType": "image/png", "buffer": PNG} for i in range(2)
    ])
    roles.nth(2).click()
    labels = page.locator("#videoImagePreview .video-image-label")
    expect(labels).to_have_text(["首帧", "尾帧"])
    first_card = page.locator("#videoImagePreview .video-image-card").first.bounding_box()
    workspace = page.locator(".video-image-workspace").bounding_box()
    assert abs(first_card["y"] - workspace["y"]) <= 1
    assert first_card["x"] >= boxes[0]["x"] + boxes[0]["width"]
    roles.nth(1).click()
    expect(labels).to_have_text(["参考图 1", "参考图 2"])
    page.evaluate("""() => {
        videoImages = Array(12).fill(videoImages[0]);
        renderVideoImagePreview();
    }""")
    roles_top = roles.first.bounding_box()["y"]
    combo = page.locator("#videoI2VPanel .video-image-action-combo")
    upload = page.locator("#videoUploadZone")
    library = page.locator("#videoI2VPanel .video-image-add-library")
    combo_box = combo.bounding_box()
    upload_box = upload.bounding_box()
    library_box = library.bounding_box()
    workspace = page.locator(".video-image-workspace").bounding_box()
    assert abs(combo_box["width"] - 108) <= 1
    assert abs(combo_box["height"] - 116) <= 1
    assert abs(combo_box["x"] + combo_box["width"] - workspace["x"] - workspace["width"]) <= 1
    assert abs(upload_box["x"] - combo_box["x"]) <= 1
    assert abs(upload_box["y"] - combo_box["y"]) <= 1
    assert abs(upload_box["width"] - combo_box["width"]) <= 2
    assert library_box["x"] >= combo_box["x"]
    assert abs(library_box["x"] + library_box["width"] - combo_box["x"] - combo_box["width"]) <= 2
    assert abs(upload_box["height"] + library_box["height"] - combo_box["height"]) <= 2
    assert abs(combo_box["y"] - workspace["y"]) <= 1
    assert combo_box["y"] + combo_box["height"] <= workspace["y"] + workspace["height"] + 1
    page.locator("#videoI2VPanel .video-upload-list").evaluate("el => el.scrollTop = 10000")
    assert roles.first.bounding_box()["y"] == roles_top
    assert combo.bounding_box() == combo_box
    assert upload.bounding_box() == upload_box
    assert library.bounding_box() == library_box
    page.screenshot(path=str(tmp_path / f"video-assets-{width}.png"))


def test_video_gallery_is_singleton_and_can_close_while_loading(page):
    show_video(page)
    page.evaluate("""() => {
        window.galleryRequests = 0;
        const originalFetch = _authFetch;
        _authFetch = (url, options) => {
            if (url !== '/api/preview/images') return originalFetch(url, options);
            galleryRequests++;
            return new Promise(resolve => { window.finishGallery = resolve; });
        };
        openVideoPreviewPicker();
        openVideoPreviewPicker();
    }""")
    expect(page.locator("#videoPickerOverlay")).to_have_count(1)
    assert page.evaluate("galleryRequests") == 1
    page.get_by_role("button", name="关闭图片选择", exact=True).click()
    expect(page.locator("#videoPickerOverlay")).to_have_count(0)
    page.evaluate("finishGallery({ok:true,json:async()=>({items:[]})})")
    expect(page.locator("#videoPickerOverlay")).to_have_count(0)


@pytest.mark.parametrize("method", ["close", "escape", "backdrop", "select"])
@pytest.mark.parametrize("mode", ["i2vid", "keyframes"])
def test_video_gallery_close_and_select(page, tmp_path, method, mode):
    show_video(page, mode)
    source = "data:image/png;base64," + base64.b64encode(PNG).decode()
    page.route("**/api/preview/images", lambda route: route.fulfill(json={
        "items": [{"data": source, "filename": '<img src=x onerror="alert(1)">'}] * 25
    }))
    trigger = page.locator("#videoI2VPanel" if mode == "i2vid" else "#videoKeyframesPanel")
    trigger.locator(".video-image-add-library").click()
    picker = page.locator("#videoPickerOverlay")
    expect(picker.get_by_role("button", name="选择图库图片 1", exact=True)).to_be_visible()
    assert picker.locator("img").count() == 25
    assert picker.locator("[onerror]").count() == 0
    picker.locator("#videoPickerGrid").evaluate("el => el.scrollTop = 10000")
    expect(picker.get_by_role("button", name="关闭图片选择", exact=True)).to_be_in_viewport()
    if method == "close":
        picker.get_by_role("button", name="关闭图片选择", exact=True).click()
    elif method == "escape":
        page.keyboard.press("Escape")
    elif method == "backdrop":
        page.mouse.click(5, 5)
    else:
        picker.get_by_role("button", name="选择图库图片 1", exact=True).click()
        labels = trigger.locator(".video-image-label")
        expect(labels).to_have_text(["首帧" if mode == "i2vid" else "关键帧 1"])
        expect(picker).to_have_count(0)
    expect(trigger.locator(".video-image-add-library")).to_be_focused()
    page.screenshot(path=str(tmp_path / f"gallery-{mode}-{method}.png"))


def test_video_gallery_failure_and_empty_are_dismissible(page):
    show_video(page)
    for status, payload in [(503, {}), (200, {"items": []})]:
        page.route("**/api/preview/images", lambda route: route.fulfill(status=status, json=payload))
        page.evaluate("openVideoPreviewPicker()")
        expect(page.locator(".video-picker-message")).to_contain_text(
            "图库加载失败" if status == 503 else "还没有图片"
        )
        page.keyboard.press("Escape")
        expect(page.locator("#videoPickerOverlay")).to_have_count(0)


def test_multifile_read_order_and_keyframe_labels(page):
    show_video(page, "keyframes")
    result = page.evaluate("""async () => {
        const Reader = window.FileReader;
        window.FileReader = class {
            readAsDataURL(file) {
                setTimeout(() => this.onload({target:{result:file.name}}),
                    file.name === 'first' ? 50 : 0);
            }
        };
        try {
            await readVideoImageBatch([
                new File(['first'], 'first', {type:'image/png'}),
                new File(['last'], 'last', {type:'image/png'})
            ], 'keyframes');
            return kfImages;
        } finally { window.FileReader = Reader; }
    }""")
    assert result == ["first", "last"]
    expect(page.locator("#kfImagePreview .video-image-label")).to_have_text(
        ["关键帧 1 · 首帧", "关键帧 2 · 尾帧"]
    )


def test_video_new_session_does_not_interrupt_active_generation(page):
    show_video(page)
    page.locator("#videoPrompt").fill("Keep active draft")
    page.evaluate("videoActivePollTasks = {synthetic: {provider_id:'synthetic'}}")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="新会话", exact=True).click()
    expect(page.locator("#videoPrompt")).to_have_value("Keep active draft")
    assert page.evaluate("Object.keys(videoActivePollTasks)") == ["synthetic"]
    expect(page.locator(".video-tools-dialog")).not_to_be_visible()
    page.evaluate("videoActivePollTasks = {}")


def test_video_prompt_resize_is_bounded_in_short_desktop(page):
    page.set_viewport_size({"width": 1024, "height": 700})
    show_video(page)
    page.locator("#videoPrompt").fill("Synthetic prompt\n" * 100)
    handle = page.locator(".video-preview-frame .resize-handle-bottom")
    handle.focus()
    for _ in range(25):
        handle.press("ArrowUp")
    preview = page.locator("#videoPreviewPanel").bounding_box()
    button = page.locator("#videoGenBtn").bounding_box()
    assert preview["height"] >= 220
    assert button["y"] + button["height"] <= 700
    expect(page.locator("#videoPromptAuto")).to_be_in_viewport()
    page.locator("#videoPromptAuto").click()


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
