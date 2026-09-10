from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import base64
from io import BytesIO
import os
from pathlib import Path
import threading

from PIL import Image
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).parents[1]


def test_precision_inspector_model_first_disclosure_and_metadata_layout(tmp_path):
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    image_bytes = BytesIO()
    Image.new("RGB", (160, 240), color=(40, 150, 100)).save(image_bytes, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1438, "height": 994})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate("""dataUrl => {
                document.querySelector('#pageGenerate').classList.remove('hidden');
                document.querySelector('#pageGenerate').classList.add('precision-workbench');
                document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                ensurePrecisionEditPanel();
                loadPrecisionEditSourceImage(dataUrl, '', {createdAt: '2026-09-09T10:00:00Z'});
            }""", data_url)
            page.wait_for_function("() => precisionEditSession.source && precisionEditSession.source.width === 160")
            order = page.evaluate("""() => [...document.querySelector('.precision-edit-inspector').children]
                .filter(el => el.matches('#precisionTaskMonitor, .precision-model-picker, .precision-edit-actions, .precision-quick-tools'))
                .map(el => el.id || el.className)""")
            assert order == ["precisionTaskMonitor", "precisionModelPicker", "precision-edit-actions", "precision-quick-tools"]
            model = page.locator("#precisionModelPicker")
            summary = page.locator("#btnPrecisionModelPickerToggle")
            assert model.get_attribute("open") is None
            assert not page.locator("#precisionEditProviderModel").is_visible()
            summary.focus()
            page.keyboard.press("Enter")
            assert model.get_attribute("open") is not None
            assert page.locator("#precisionEditProviderModel").is_visible()
            page.keyboard.press("Space")
            assert model.get_attribute("open") is None
            for width, height in [(1438, 994), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                summary.scroll_into_view_if_needed()
                layout = page.evaluate("""() => {
                    const summary = document.querySelector('#btnPrecisionModelPickerToggle');
                    const label = document.querySelector('#precisionModelPickerTitle');
                    const smart = document.querySelector('.precision-quick-heading');
                    const smartLabel = document.querySelector('#precisionQuickToolsTitle');
                    const rect = el => el.getBoundingClientRect();
                    const centered = (a,b) => Math.abs((rect(a).left+rect(a).right)-(rect(b).left+rect(b).right)) < 2;
                    return {
                        centered: centered(summary,label) && centered(smart,smartLabel),
                        textured: getComputedStyle(summary).backgroundImage === getComputedStyle(document.querySelector('.precision-size-heading-copy')).backgroundImage,
                        smartBelowSize: rect(smart).top > rect(document.querySelector('.precision-size-tool')).bottom,
                        noOverflow: document.documentElement.scrollWidth <= window.innerWidth
                    };
                }""")
                assert all(layout.values()), layout
                page.screenshot(path=str(tmp_path / f"inspector-{width}.png"))
                page.locator("#precisionCanvasSurface").scroll_into_view_if_needed()
                badge_bounds = page.locator("#precisionCanvasImageInfo").bounding_box()
                surface_bounds = page.locator("#precisionCanvasSurface").bounding_box()
                assert badge_bounds and surface_bounds
                assert badge_bounds["x"] >= surface_bounds["x"]
                assert badge_bounds["x"] + badge_bounds["width"] <= surface_bounds["x"] + surface_bounds["width"]
                assert "160 × 240" in page.locator("#precisionCanvasImageInfo").inner_text()
                assert "2026-09-09" in page.locator("#precisionCanvasImageInfo").inner_text()
                page.screenshot(path=str(tmp_path / f"metadata-{width}.png"))
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _launch_browser(playwright, **kwargs):
    """Allow local acceptance runs to use an installed Chromium executable."""
    executable_path = os.environ.get("GENBOX_PLAYWRIGHT_EXECUTABLE")
    if executable_path:
        return playwright.chromium.launch(executable_path=executable_path, **kwargs)
    return playwright.chromium.launch(**kwargs)


def test_precision_canvas_shift_wheel_zoom_and_middle_reset_keep_resize_handle_fixed():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    image_bytes = BytesIO()
    Image.new("RGB", (40, 30), color=(30, 90, 150)).save(image_bytes, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.add_init_script("localStorage.setItem('genbox_precision_quick_start_v1', 'seen');")
            page.set_default_timeout(3000)
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate(
                """(dataUrl) => {
                    switchNav('generate', document.querySelector('#navGen'));
                    setCreatorWorkbenchMode('image', 'precision');
                    loadPrecisionEditSourceImage(dataUrl, '');
                }""",
                data_url,
            )
            shell = page.locator("#precisionCanvasShell")
            page.wait_for_function("() => precisionEditSourceImageData && document.querySelector('#precisionCanvasResizeHandle').offsetParent !== null")
            shell.scroll_into_view_if_needed()
            shell.hover()
            box = shell.bounding_box()
            assert box
            assert page.evaluate("""([x, y]) => {
                const hit = document.elementFromPoint(x, y);
                return !!hit && !!hit.closest('#precisionCanvasShell');
            }""", [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
            handle_before = page.locator("#precisionCanvasResizeHandle").bounding_box()
            assert handle_before
            page.evaluate("""() => {
                window.__wheelProbe = [];
                document.addEventListener('wheel', event => {
                    const shell = document.querySelector('#precisionCanvasShell');
                    const box = shell.getBoundingClientRect();
                    window.__wheelProbe.push({
                        target: event.target.id, shift: event.shiftKey,
                        x: event.clientX, y: event.clientY,
                        dx: event.deltaX, dy: event.deltaY,
                        hotspot: precisionCanvasZoomHotspotContains(event, shell),
                        rect: {x: box.x, y: box.y, width: box.width, height: box.height},
                        loaded: !!precisionEditSourceImageData,
                        bound: shell.dataset.precisionZoomBound
                    });
                }, {capture: true, once: true});
            }""")
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.keyboard.down("Shift")
            page.mouse.wheel(0, -120)
            try:
                expect(page.locator("#precisionViewZoom")).to_have_value("110")
            except AssertionError:
                raise AssertionError(page.evaluate("() => window.__wheelProbe")) from None
            page.keyboard.up("Shift")
            handle_after = page.locator("#precisionCanvasResizeHandle").bounding_box()
            assert handle_after
            assert abs((handle_after["x"] + handle_after["width"]) - (box["x"] + box["width"])) <= 1
            assert abs((handle_after["y"] + handle_after["height"]) - (box["y"] + box["height"])) <= 1
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, button="middle")
            page.wait_for_function("() => Number(document.querySelector('#precisionViewZoom').value) === 100")
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_professional_cutout_dock_stays_visible_after_portaling_to_document_body():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    image_bytes = BytesIO()
    Image.new("RGB", (40, 30), color=(30, 90, 150)).save(image_bytes, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.set_default_timeout(3000)
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate(
                """(dataUrl) => {
                    document.querySelector('#pageGenerate').classList.remove('hidden');
                    document.querySelector('#pageGenerate').classList.add('precision-workbench');
                    document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                    loadPrecisionEditSourceImage(dataUrl, '');
                    openPrecisionCutoutProfessionalDialog();
                }""",
                data_url,
            )
            dock = page.locator("#precisionCutoutProfessionalDialog")
            card = page.locator("#precisionCutoutProfessionalDialog .precision-cutout-professional-card")
            page.wait_for_function("() => !document.querySelector('#precisionCutoutProfessionalDialog').hidden")
            assert page.evaluate("() => document.querySelector('#precisionCutoutProfessionalDialog').parentElement === document.body")
            assert page.evaluate("() => getComputedStyle(document.querySelector('#precisionCutoutProfessionalDialog')).position") == "fixed"
            page.wait_for_function(
                """() => {
                    const shell = document.querySelector('#precisionCanvasShell').getBoundingClientRect();
                    const card = document.querySelector('#precisionCutoutProfessionalDialog .precision-cutout-professional-card').getBoundingClientRect();
                    return Math.abs(shell.top - card.top) <= 2 && Math.abs(shell.bottom - card.bottom) <= 2;
                }"""
            )
            dock_box = dock.bounding_box()
            card_box = card.bounding_box()
            assert dock_box and card_box
            assert card_box["x"] >= 0 and card_box["y"] >= 0
            assert card_box["x"] + card_box["width"] <= 1200
            assert card_box["y"] + card_box["height"] <= 900
            assert page.locator("#btnPrecisionCutoutProfessionalRun").is_visible()
            assert page.locator("#precisionCutoutProfessionalAlgorithm").is_visible()
            assert page.locator("#precisionCutoutProfessionalResizeHandle").is_visible()
            assert page.locator("#btnPrecisionCutoutProfessionalCollapse").is_visible()
            assert page.locator("#btnPrecisionCutoutProfessionalClose").is_visible()
            shell_box = page.locator("#precisionCanvasShell").bounding_box()
            assert shell_box
            assert shell_box["x"] + shell_box["width"] < card_box["x"]
            assert abs(shell_box["y"] - card_box["y"]) <= 2
            assert abs((shell_box["y"] + shell_box["height"]) - (card_box["y"] + card_box["height"])) <= 2
            assert page.evaluate(
                """() => {
                    const card = document.querySelector('#precisionCutoutProfessionalDialog .precision-cutout-professional-card');
                    const cardBox = card.getBoundingClientRect();
                    const bodyBox = document.querySelector('.precision-cutout-professional-body').getBoundingClientRect();
                    const background = getComputedStyle(card).backgroundImage;
                    return background !== 'none'
                      && bodyBox.left >= cardBox.left
                      && bodyBox.right <= cardBox.right
                      && [...document.querySelectorAll('.precision-cutout-professional-body select, .precision-cutout-professional-actions button, .precision-cutout-professional-refine')]
                        .every((element) => {
                            const box = element.getBoundingClientRect();
                            return box.left >= cardBox.left && box.right <= cardBox.right;
                        });
                }"""
            )
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_precision_session_gallery_is_collapsed_and_keeps_result_selection_in_browser():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            page.evaluate(
                """() => {
                    document.querySelector('#pageGenerate').classList.remove('hidden');
                    document.querySelector('#pageGenerate').classList.add('precision-workbench');
                    document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                    window.precisionEditSession = {
                        source: { id: 'original', data: 'data:image/png;base64,a', label: '原图', createdAt: '2026-09-01T10:00:00Z' },
                        versions: [
                            { id: 'v1', data: 'data:image/png;base64,b', label: '1', createdAt: '2026-09-02T10:00:00Z', prompt: 'one' },
                            { id: 'v2', data: 'data:image/png;base64,c', label: '2', createdAt: '2026-09-03T10:00:00Z', prompt: 'two' },
                        ],
                        selectedVersionId: 'v2',
                        view: 'after',
                    };
                    renderPrecisionEditSession();
                }"""
            )
            gallery = page.locator("#precisionSessionGallery .precision-session-thumb")
            count = page.locator("#precisionSessionResultCount")
            showcase_toggle = page.locator("#btnPrecisionSessionShowcaseToggle")
            showcase_content = page.locator("#precisionSessionShowcaseContent")
            assert gallery.count() == 2
            assert count.text_content() == "2"
            assert showcase_toggle.get_attribute("aria-expanded") == "false"
            assert showcase_content.get_attribute("aria-hidden") == "true"
            assert showcase_content.get_attribute("inert") is not None

            showcase_toggle.click()
            assert showcase_toggle.get_attribute("aria-expanded") == "true"
            assert showcase_content.get_attribute("aria-hidden") == "false"
            assert showcase_content.get_attribute("inert") is None

            gallery.nth(0).click()
            assert page.evaluate("window.precisionEditSession.selectedVersionId") == "v1"
            assert page.evaluate("window.precisionEditSession.view") == "after"
            page.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_precision_session_gallery_receives_successful_generation_result():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            page.evaluate(
                """() => {
                    window.precisionSourceLoadGeneration = 4;
                    window.precisionEditSession = {
                        source: { id: 'original', data: 'data:image/png;base64,a', label: '原图' },
                        versions: [],
                        selectedVersionId: 'original',
                        view: 'before',
                    };
                    appendPrecisionEditVersion({
                        success: true,
                        local_path: 'session-result.png',
                        prompt: '保持主体并扩展画面',
                    }, 4);
                }"""
            )
            thumb = page.locator("#precisionSessionGallery .precision-session-thumb")
            assert thumb.count() == 1
            assert page.locator("#precisionSessionResultCount").text_content() == "1"
            assert page.locator("#precisionSessionGallery img").get_attribute("src").endswith("session-result.png")
            assert page.locator("#precisionSessionGallery").inner_text().find("1") >= 0
            page.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_precision_workflow_history_filter_is_full_width_and_owns_history_controls():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.set_default_timeout(3000)
            workflow_id = "pw_" + ("a" * 32)
            first_result = "pv_" + ("b" * 24)
            second_result = "pv_" + ("c" * 24)
            version_images = {}
            for version_id, size in [("original", (40, 30)), (first_result, (24, 48)), (second_result, (64, 32))]:
                image_bytes = BytesIO()
                Image.new("RGB", size, color=(30, 90, 150)).save(image_bytes, format="PNG")
                version_images[version_id] = image_bytes.getvalue()
            workflow = {
                "workflow_id": workflow_id,
                "updated_at": "2026-09-03T10:00:00Z",
                "edit_count": 2,
                "summary": {"latest_size": "1024x1024"},
                "versions": [
                    {"version_id": "original", "kind": "source", "created_at": "2026-09-01T10:00:00Z", "available": True, "thumbnail": f"/api/precision/workflows/{workflow_id}/versions/original/thumb", "image_url": f"/api/precision/workflows/{workflow_id}/versions/original/image"},
                    {"version_id": first_result, "parent_version_id": "original", "kind": "result", "created_at": "2026-09-02T10:00:00Z", "available": True, "thumbnail": f"/api/precision/workflows/{workflow_id}/versions/{first_result}/thumb", "image_url": f"/api/precision/workflows/{workflow_id}/versions/{first_result}/image"},
                    {"version_id": second_result, "parent_version_id": first_result, "kind": "result", "created_at": "2026-09-03T10:00:00Z", "available": True, "thumbnail": f"/api/precision/workflows/{workflow_id}/versions/{second_result}/thumb", "image_url": f"/api/precision/workflows/{workflow_id}/versions/{second_result}/image", "annotation_snapshot": {"annotation_contract": "genbox-annotation-v3", "annotations": [{"type": "ellipse", "label": 1, "instruction": "Make the badge blue.", "x": 0.2, "y": 0.2, "width": 0.3, "height": 0.2}], "precision_strategy": "fine", "precision_selection_mode": "annotation", "precision_selection_feather": 0}},
                ],
                "restore": {"version_id": second_result, "base_version_id": first_result, "image_url": f"/api/precision/workflows/{workflow_id}/versions/{second_result}/image", "annotation_snapshot": {"annotation_contract": "genbox-annotation-v3", "annotations": [{"type": "ellipse", "label": 1, "instruction": "Make the badge blue.", "x": 0.2, "y": 0.2, "width": 0.3, "height": 0.2}], "precision_strategy": "fine", "precision_selection_mode": "annotation", "precision_selection_feather": 0}},
            }
            workflow_list = {key: value for key, value in workflow.items() if key != "restore"}
            workflow_list["versions"] = [{key: value for key, value in version.items() if key != "annotation_snapshot"} for version in workflow["versions"]]
            workflow_list["restore"] = {key: value for key, value in workflow["restore"].items() if key != "annotation_snapshot" and key != "base_version_id"}

            workflow_requests = []

            def route_api(route):
                url = route.request.url
                if f"/api/precision/workflows/{workflow_id}/versions/" in url:
                    version_id = url.split("/versions/")[1].split("/")[0]
                    route.fulfill(status=200, body=version_images[version_id], content_type="image/png")
                elif f"/api/precision/workflows/{workflow_id}" in url:
                    route.fulfill(status=200, json={"workflow": workflow})
                elif "/api/precision/workflows?" in url:
                    workflow_requests.append(url)
                    route.fulfill(status=200, json={"items": [workflow_list]})
                else:
                    route.fulfill(status=404, json={"detail": "test only"})

            page.route("**/api/**", route_api)
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate(
                """() => {
                    document.querySelector('#pageGenerate').classList.remove('hidden');
                    document.querySelector('#pageGenerate').classList.add('precision-workbench');
                    document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                    window.precisionEditSession = {
                        source: { id: 'original', data: 'data:image/png;base64,a' },
                        versions: [{ id: 'v1', data: 'data:image/png;base64,b', createdAt: '2026-09-03T10:00:00' }],
                        selectedVersionId: 'v1', view: 'after'
                    };
                    renderPrecisionEditSession();
                }"""
            )
            showcase_toggle = page.locator("#btnPrecisionSessionShowcaseToggle")
            showcase_content = page.locator("#precisionSessionShowcaseContent")
            workflow_filter = page.locator("#btnPrecisionWorkflowHistoryFilter")
            popover = page.locator("#precisionWorkflowHistoryFilterPopover")
            assert showcase_toggle.get_attribute("aria-expanded") == "false"
            assert showcase_content.get_attribute("aria-hidden") == "true"
            assert showcase_content.get_attribute("inert") is not None
            showcase_toggle.click()
            assert showcase_toggle.get_attribute("aria-expanded") == "true"
            assert showcase_content.get_attribute("aria-hidden") == "false"
            assert showcase_content.get_attribute("inert") is None

            layout = workflow_filter.evaluate(
                """button => {
                    const filters = button.closest('.precision-workflow-history-filters');
                    const label = button.querySelector('[data-i18n="creator.precision_workflow_history_filter_trigger"]');
                    if (!filters || !label) return null;
                    const buttonBox = button.getBoundingClientRect();
                    const filtersBox = filters.getBoundingClientRect();
                    const labelBox = label.getBoundingClientRect();
                    return {
                        buttonWidth: buttonBox.width,
                        filtersWidth: filtersBox.width,
                        buttonCenter: buttonBox.left + (buttonBox.width / 2),
                        labelCenter: labelBox.left + (labelBox.width / 2),
                        minHeight: Number.parseFloat(getComputedStyle(button).minHeight),
                        galleryTop: document.querySelector('#precisionSessionGallery').getBoundingClientRect().top,
                        buttonBottom: buttonBox.bottom,
                    };
                }"""
            )
            assert layout is not None
            assert abs(layout["buttonWidth"] - layout["filtersWidth"]) <= 1
            assert abs(layout["buttonCenter"] - layout["labelCenter"]) <= 1
            assert layout["minHeight"] >= 38
            assert layout["buttonBottom"] <= layout["galleryTop"]
            assert workflow_filter.get_attribute("aria-expanded") == "false"
            assert workflow_filter.get_attribute("aria-haspopup") == "dialog"
            assert popover.get_attribute("hidden") is not None

            assert popover.locator("#precisionWorkflowHistoryDateFrom").count() == 0
            assert popover.locator("#precisionWorkflowHistoryDateTo").count() == 0
            assert popover.locator("#precisionWorkflowHistoryCalendar").count() == 1
            assert popover.locator("#precisionWorkflowHistoryList").count() == 1
            workflow_filter.click()
            assert workflow_filter.get_attribute("aria-expanded") == "true"
            assert popover.get_attribute("hidden") is None
            assert popover.get_attribute("aria-modal") == "true"
            calendar = popover.locator("#precisionWorkflowHistoryCalendar")
            assert calendar.get_attribute("role") == "grid"
            assert calendar.locator(".precision-workflow-history-calendar-day.has-history").count() == 3
            assert popover.locator("[data-workflow-date-range]").count() == 7
            calendar.locator("[data-workflow-date='2026-09-03']").click()
            page.wait_for_timeout(100)
            assert calendar.locator("[data-workflow-date='2026-09-03']").get_attribute("aria-pressed") == "true"
            assert popover.get_attribute("hidden") is None
            assert any("date_from=2026-09-03" in request and "date_to=2026-09-03" in request for request in workflow_requests)
            popover.locator("#btnPrecisionWorkflowHistoryDateClear").click()
            page.wait_for_timeout(100)
            assert calendar.locator("[data-workflow-date='2026-09-03']").get_attribute("aria-pressed") == "false"
            history_row = page.locator("#precisionWorkflowHistoryList .precision-workflow-history-select")
            assert history_row.count() == 1
            history_images = history_row.locator(".precision-workflow-history-version img")
            assert history_images.count() == 3
            assert history_images.nth(0).get_attribute("src").endswith("/versions/original/thumb")
            assert history_images.nth(1).get_attribute("src").endswith(f"/versions/{first_result}/thumb")
            assert history_images.nth(2).get_attribute("src").endswith(f"/versions/{second_result}/thumb")
            history_row.click()
            action = page.locator("#precisionWorkflowHistoryActionPopover")
            page.wait_for_function("() => !document.querySelector('#precisionWorkflowHistoryActionPopover').hidden")
            assert action.get_attribute("hidden") is None
            assert action.locator("button").count() == 2
            page.once("dialog", lambda dialog: dialog.accept())
            action.locator("button").nth(1).click()
            page.wait_for_function(
                """() => window.precisionEditSession.selectedVersionId === 'pv_cccccccccccccccccccccccc' &&
                    window.precisionEditSession.baseVersionId === 'pv_bbbbbbbbbbbbbbbbbbbbbbbb' &&
                    window.precisionEditSession.versions.length === 2 &&
                    !!window.precisionEditSession.source.data &&
                    window.precisionEditSession.versions.every(version => !!version.data) &&
                    window.precisionEditObjects.length === 1 &&
                    window.precisionEditObjects[0].instruction === 'Make the badge blue.'"""
            )
            assert page.evaluate("() => precisionEditSession.view") == "compare"
            badge = page.locator("#precisionCanvasImageInfo")
            page.wait_for_function(
                "() => document.querySelector('#precisionCanvasImageInfo').textContent.includes('24 × 48') && document.querySelector('#precisionCanvasImageInfo').textContent.includes('64 × 32')"
            )
            assert "2026-09-02" in badge.inner_text()
            assert "2026-09-03" in badge.inner_text()
            page.evaluate("() => { precisionEditSession.view = 'after'; renderPrecisionEditSession(); }")
            assert "64 × 32" in badge.inner_text()
            assert "24 × 48" not in badge.inner_text()
            page.evaluate("() => { precisionEditSession.view = 'before'; renderPrecisionEditSession(); }")
            assert "24 × 48" in badge.inner_text()
            page.evaluate("() => { precisionEditSession.selectedVersionId = 'original'; precisionEditSession.view = 'after'; renderPrecisionEditSession(); }")
            page.wait_for_function("() => document.querySelector('#precisionCanvasImageInfo').textContent.includes('40 × 30')")
            assert "2026-09-01" in badge.inner_text()
            page.keyboard.press("Escape")
            assert action.get_attribute("hidden") is not None
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_precision_source_menu_and_two_row_toolbar_fit_common_viewports():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 1000})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate(
                """() => {
                    document.querySelector('#pageGenerate').classList.remove('hidden');
                    document.querySelector('#pageGenerate').classList.add('precision-workbench');
                    document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                    window.precisionEditSourceImageData = 'data:image/png;base64,c291cmNl';
                    updatePrecisionSourceActions();
                }"""
            )

            trigger = page.locator("#btnPrecisionReplaceSource")
            menu = page.locator("#precisionSourceMenu")
            assert trigger.is_visible()
            assert "更换图片" in trigger.inner_text()
            trigger.click()
            assert menu.is_visible()
            assert "本地上传" in menu.inner_text()
            assert "从图库选择" in menu.inner_text()
            assert page.evaluate("document.activeElement.id") == "btnPrecisionReplaceLocal"
            page.keyboard.press("ArrowDown")
            assert page.evaluate("document.activeElement.id") == "btnPrecisionReplaceFromGallery"
            page.keyboard.press("Escape")
            assert not menu.is_visible()
            assert page.evaluate("document.activeElement.id") == "btnPrecisionReplaceSource"

            page.evaluate("window.genIsPrecisionTask = true; window.genCurrentGenId = 'active-task'; updatePrecisionSourceActions();")
            assert trigger.is_disabled()
            assert page.locator("#precisionReplaceDisabledHint").is_visible()
            page.evaluate("window.genIsPrecisionTask = false; window.genCurrentGenId = null; updatePrecisionSourceActions();")

            for width, height in [(1200, 1000), (760, 900), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("window.dispatchEvent(new Event('resize'))")
                metrics = page.evaluate(
                    """() => {
                        const toolbar = document.querySelector('.precision-toolbar');
                        const primary = document.querySelector('.precision-toolbar-primary');
                        const history = document.querySelector('.precision-toolbar-history');
                        const bounds = (node) => {
                            const box = node.getBoundingClientRect();
                            return { left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: box.width };
                        };
                        return {
                            clientWidth: toolbar.clientWidth,
                            scrollWidth: toolbar.scrollWidth,
                            toolbar: bounds(toolbar),
                            primary: bounds(primary),
                            history: bounds(history),
                            controls: Array.from(toolbar.querySelectorAll('button, input')).map(bounds),
                        };
                    }"""
                )
                assert metrics["clientWidth"] > 0
                assert metrics["scrollWidth"] <= metrics["clientWidth"] + 1
                assert metrics["history"]["top"] >= metrics["primary"]["bottom"] - 1
                assert abs(metrics["history"]["left"] - metrics["toolbar"]["left"]) <= 1
                assert metrics["history"]["right"] <= metrics["toolbar"]["right"] + 1
                for control in metrics["controls"]:
                    assert control["left"] >= metrics["toolbar"]["left"] - 1
                    assert control["right"] <= metrics["toolbar"]["right"] + 1
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_loaded_precision_canvas_real_pointer_fullscreen_and_mobile_menu_contracts():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright, headless=os.environ.get("GENBOX_HEADED") != "1")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.add_init_script("localStorage.setItem('genbox_precision_quick_start_v1', 'seen');")
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.evaluate(
                """() => {
                    switchNav('generate', document.querySelector('#navGen'));
                    setCreatorWorkbenchMode('image', 'precision');
                    const source = '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="640" height="480" fill="#c24"/></svg>';
                    loadPrecisionEditSourceImage('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source), 'synthetic browser contract');
                }"""
            )
            page.wait_for_function("window.precisionEditSourceWidth === 640 && window.precisionEditSourceHeight === 480")

            for width, height in [(390, 844), (937, 920), (1200, 800)]:
                page.set_viewport_size({"width": width, "height": height})
                session_metrics = page.evaluate(
                    """() => {
                        const session = document.querySelector('#precisionSessionPanel');
                        const actions = document.querySelector('.precision-session-fullscreen-actions');
                        const bounds = (node) => {
                            const box = node.getBoundingClientRect();
                            return { left: box.left, right: box.right, width: box.width };
                        };
                        return {
                            session: bounds(session),
                            sessionClientWidth: session.clientWidth,
                            sessionScrollWidth: session.scrollWidth,
                            actions: bounds(actions),
                            children: Array.from(actions.querySelectorAll('button')).map(bounds),
                        };
                    }"""
                )
                assert session_metrics["sessionScrollWidth"] <= session_metrics["sessionClientWidth"] + 1
                assert session_metrics["actions"]["left"] >= session_metrics["session"]["left"] - 1
                assert session_metrics["actions"]["right"] <= session_metrics["session"]["right"] + 1
                for control in session_metrics["children"]:
                    assert control["left"] >= session_metrics["session"]["left"] - 1
                    assert control["right"] <= session_metrics["session"]["right"] + 1
                canvas = page.locator("#precisionAnnotationCanvas")
                canvas.scroll_into_view_if_needed()
                box = canvas.bounding_box()
                assert box
                point = {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}
                page.wait_for_function(
                    "([x, y]) => document.elementFromPoint(x, y)?.id === 'precisionAnnotationCanvas'",
                    arg=[point["x"], point["y"]],
                )
                assert page.evaluate("([x, y]) => document.elementFromPoint(x, y)?.id", [point["x"], point["y"]]) == "precisionAnnotationCanvas"

                page.evaluate("setPrecisionViewZoom(140)")
                page.mouse.click(point["x"], point["y"], button="middle")
                assert page.evaluate("window.precisionViewZoom") == 100
                assert page.locator("#precisionViewZoom").input_value() == "100"
                assert page.locator("#precisionViewZoomValue").text_content() == "100%"

                page.evaluate("setPrecisionViewZoom(140)")
                page.mouse.move(point["x"], point["y"])
                page.mouse.down(button="middle")
                page.mouse.move(point["x"] - 24, point["y"], steps=3)
                page.mouse.up(button="middle")
                assert page.evaluate("window.precisionViewZoom") == 140
                assert page.evaluate("document.querySelector('#precisionCanvasShell').scrollLeft") > 0
                page.evaluate("setPrecisionViewZoom(100, { resetScroll: true })")

                page.evaluate(
                    """() => {
                        precisionEditSession.source.prompt = 'original prompt';
                        precisionEditSession.versions = [{
                            id: 'viewer-version-1', label: '1',
                            data: precisionEditSession.source.data,
                            prompt: 'first edit prompt',
                            createdAt: '2026-09-05T10:00:00Z'
                        }];
                        precisionEditSession.selectedVersionId = 'viewer-version-1';
                        precisionEditSession.view = 'before';
                        renderPrecisionEditSession();
                    }"""
                )

                image_fullscreen = page.locator("#btnPrecisionImageFullscreen")
                assert image_fullscreen.is_visible()
                image_fullscreen.click()
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.locator("#precisionImageFullscreenImg").get_attribute("src").startswith("data:image/svg+xml")
                prompt_entries = page.locator("#precisionImageFullscreenPromptHistory .precision-image-fullscreen-prompt-entry")
                assert prompt_entries.count() == 2
                assert prompt_entries.nth(0).inner_text().startswith("原图提示词")
                assert "original prompt" in prompt_entries.nth(0).inner_text()
                assert prompt_entries.nth(1).inner_text().startswith("改图 1 提示词")
                assert "first edit prompt" in prompt_entries.nth(1).inner_text()
                assert page.locator("#precisionImageFullscreenPromptHistory .selected").count() == 1
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

                page.evaluate("setPrecisionEditTool('brush')")
                object_count = page.evaluate("window.precisionEditObjects.length")
                # Opening the viewer may scroll the triggering button into view.
                # Resolve the canvas again instead of reusing pre-viewer coordinates.
                canvas.dblclick(button="left", delay=20)
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("window.precisionEditObjects.length") == object_count
                assert page.locator("#precisionImageFullscreenImg").get_attribute("src").startswith("data:image/svg+xml")
                assert page.evaluate("document.fullscreenElement") is None
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

                def double_click_with_small_drift():
                    canvas.scroll_into_view_if_needed()
                    current_box = canvas.bounding_box()
                    assert current_box
                    point = {"x": current_box["x"] + current_box["width"] / 2, "y": current_box["y"] + current_box["height"] / 2}
                    assert page.evaluate("([x,y]) => document.elementFromPoint(x,y)?.id", [point["x"], point["y"]]) == "precisionAnnotationCanvas"
                    page.mouse.move(point["x"], point["y"])
                    page.mouse.down(button="left")
                    page.mouse.move(point["x"] + 2, point["y"] + 1, steps=2)
                    page.mouse.up(button="left")
                    page.mouse.move(point["x"] + 1, point["y"] + 2)
                    page.mouse.down(button="left")
                    page.mouse.move(point["x"] + 3, point["y"] + 2, steps=2)
                    page.mouse.up(button="left")

                page.evaluate(
                    """() => {
                        precisionEditObjects = [];
                        precisionEditHistory = [];
                        precisionEditRedo = [];
                        precisionEditSelectedId = null;
                        setPrecisionEditTool('text');
                        renderPrecisionEditCanvas();
                    }"""
                )
                double_click_with_small_drift()
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("window.precisionEditObjects.length") == 0
                assert page.locator("#precisionTextEditor").evaluate("node => node.classList.contains('hidden')")
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

                page.evaluate(
                    """() => {
                        precisionEditObjects = [{
                            id: 'double-click-eraser-brush', type: 'brush', label: 1,
                            color: '#ef4444', strokeWidth: 5,
                            points: [{ x: 0.35, y: 0.5 }, { x: 0.65, y: 0.5 }]
                        }];
                        precisionEditHistory = [];
                        precisionEditRedo = [];
                        precisionEditSelectedId = 'double-click-eraser-brush';
                        setStatus('');
                        setPrecisionEditTool('eraser');
                        renderPrecisionEditCanvas();
                    }"""
                )
                eraser_before = page.evaluate("JSON.stringify(window.precisionEditObjects)")
                double_click_with_small_drift()
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("JSON.stringify(window.precisionEditObjects)") == eraser_before
                assert page.locator("#statusLeft").text_content() != "已删除选中的标注"
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

                page.evaluate(
                    """() => {
                        precisionEditObjects = [];
                        precisionEditHistory = [];
                        precisionEditRedo = [];
                        precisionEditSelectedId = null;
                        setPrecisionEditTool('brush');
                        renderPrecisionEditCanvas();
                        syncPrecisionAnnotationInstructionPopover();
                    }"""
                )
                double_click_with_small_drift()
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("window.precisionEditObjects.length") == 0
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

                trigger = page.locator("#btnPrecisionReplaceSource")
                trigger.scroll_into_view_if_needed()
                trigger.click()
                menu_metrics = page.evaluate(
                    """() => {
                        const menu = document.querySelector('#precisionSourceMenu');
                        const rect = menu.getBoundingClientRect();
                        const items = Array.from(menu.querySelectorAll('[role="menuitem"]')).map((item) => {
                            const itemRect = item.getBoundingClientRect();
                            const hit = document.elementFromPoint(itemRect.left + itemRect.width / 2, itemRect.top + itemRect.height / 2);
                            return {
                                id: item.id,
                                left: itemRect.left,
                                right: itemRect.right,
                                top: itemRect.top,
                                bottom: itemRect.bottom,
                                scrollWidth: item.scrollWidth,
                                clientWidth: item.clientWidth,
                                scrollHeight: item.scrollHeight,
                                clientHeight: item.clientHeight,
                                hitId: hit && hit.closest('[role="menuitem"]') && hit.closest('[role="menuitem"]').id,
                            };
                        });
                        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, viewportWidth: innerWidth, viewportHeight: innerHeight, items };
                    }"""
                )
                assert menu_metrics["left"] >= 0
                assert menu_metrics["right"] <= menu_metrics["viewportWidth"]
                assert menu_metrics["top"] >= 0
                assert menu_metrics["bottom"] <= menu_metrics["viewportHeight"]
                assert [item["id"] for item in menu_metrics["items"]] == ["btnPrecisionReplaceLocal", "btnPrecisionReplaceFromGallery"]
                for item in menu_metrics["items"]:
                    assert item["scrollWidth"] <= item["clientWidth"] + 1
                    assert item["scrollHeight"] <= item["clientHeight"] + 1
                    assert item["hitId"] == item["id"]

                page.keyboard.press("ArrowDown")
                assert page.evaluate("document.activeElement.id") == "btnPrecisionReplaceFromGallery"
                page.keyboard.press("Escape")
                assert not page.locator("#precisionSourceMenu").is_visible()
                assert page.evaluate("document.activeElement.id") == "btnPrecisionReplaceSource"
                trigger.click()
                page.locator("#precisionCanvasDimensions").click()
                assert not page.locator("#precisionSourceMenu").is_visible()

            page.evaluate(
                """() => {
                    const image = (color) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
                        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="640" height="480" fill="' + color + '"/></svg>'
                    );
                    window.__precisionVisibleVersions = {
                        original: image('#2463eb'),
                        before: image('#d97706'),
                        after: image('#15803d'),
                    };
                    precisionEditSession = {
                        source: { id: 'original', label: '原图', data: window.__precisionVisibleVersions.original },
                        versions: [
                            { id: 'version-1', label: '第一版', data: window.__precisionVisibleVersions.before, parentId: 'original' },
                            { id: 'version-2', label: '第二版', data: window.__precisionVisibleVersions.after, parentId: 'version-1' },
                        ],
                        selectedVersionId: 'version-2',
                        baseVersionId: 'original',
                        taskBaseVersionId: null,
                        view: 'before',
                        taskId: null,
                    };
                    renderPrecisionEditSession();
                }"""
            )
            compare_stage = page.locator("#precisionCompareStage")
            compare_stage.scroll_into_view_if_needed()
            compare_box = compare_stage.bounding_box()
            assert compare_box

            def dispatch_visible_version_double_click(view, ratio, expected_key):
                page.evaluate("(view) => setPrecisionVersionView(view)", view)
                page.evaluate(
                    """({ x, y }) => document.querySelector('#precisionCompareStage').dispatchEvent(
                        new MouseEvent('dblclick', { bubbles: true, cancelable: true, clientX: x, clientY: y })
                    )""",
                    {"x": compare_box["x"] + compare_box["width"] * ratio, "y": compare_box["y"] + compare_box["height"] / 2},
                )
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("([key]) => document.querySelector('#precisionImageFullscreenImg').getAttribute('src') === window.__precisionVisibleVersions[key]", [expected_key])
                page.keyboard.press("Escape")
                page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

            dispatch_visible_version_double_click("before", 0.5, "before")
            dispatch_visible_version_double_click("after", 0.5, "after")
            page.evaluate("updatePrecisionCompareSlider(50)")
            dispatch_visible_version_double_click("compare", 0.25, "after")
            dispatch_visible_version_double_click("compare", 0.75, "before")

            page.evaluate(
                """({ x, y }) => document.querySelector('#precisionAnnotationCanvas').dispatchEvent(
                    new MouseEvent('dblclick', { bubbles: true, cancelable: true, clientX: x, clientY: y })
                )""",
                {"x": point["x"], "y": point["y"]},
            )
            page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
            assert page.evaluate("document.querySelector('#precisionImageFullscreenImg').getAttribute('src') === window.__precisionVisibleVersions.original")
            page.keyboard.press("Escape")
            page.wait_for_function("document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")

            page.set_viewport_size({"width": 390, "height": 844})
            fullscreen = page.locator("#btnPrecisionFullscreen")
            fullscreen.scroll_into_view_if_needed()
            fullscreen.click()
            page.wait_for_function("document.fullscreenElement && document.fullscreenElement.id === 'panelPrecisionEdit'")
            assert fullscreen.get_attribute("aria-pressed") == "true"
            page.keyboard.press("Escape")
            page.wait_for_function("document.fullscreenElement === null")
            page.wait_for_function("document.querySelector('#btnPrecisionFullscreen').getAttribute('aria-pressed') === 'false'")
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
