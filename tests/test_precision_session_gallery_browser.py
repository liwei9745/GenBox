from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]


def test_precision_session_gallery_filters_and_clears_results_in_browser():
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
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
            page.goto(f"http://127.0.0.1:{server.server_port}/static/index.html", wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            page.evaluate(
                """() => {
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
            assert gallery.count() == 2
            assert count.text_content() == "2"

            # The static fixture keeps the precision panel hidden; dispatch the
            # button's native click handler without coupling this focused test
            # to the full navigation shell's visibility state.
            gallery.nth(0).evaluate("el => el.click()")
            assert page.evaluate("window.precisionEditSession.selectedVersionId") == "v1"
            assert page.evaluate("window.precisionEditSession.view") == "after"

            page.evaluate(
                """() => {
                    const input = document.querySelector('#precisionSessionDateFrom');
                    input.value = '2026-09-03';
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }"""
            )
            assert gallery.count() == 1
            assert count.text_content() == "1"

            page.evaluate(
                """() => {
                    clearPrecisionSessionDateFilter();
                }"""
            )
            assert gallery.count() == 2
            assert count.text_content() == "2"
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
            browser = playwright.chromium.launch(headless=True)
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


def test_precision_session_calendar_filter_is_collapsed_and_highlights_result_dates():
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
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
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
            toggle = page.locator("#precisionSessionDateToggle")
            popover = page.locator("#precisionSessionDatePopover")
            heading = page.locator(".precision-session-showcase-heading")
            assert "精准改图图库" in heading.inner_text()
            assert toggle.locator("xpath=ancestor::div[contains(@class, 'precision-session-showcase-heading')]").count() == 1
            assert toggle.get_attribute("aria-expanded") == "false"
            assert toggle.get_attribute("aria-haspopup") == "dialog"
            assert popover.get_attribute("hidden") is not None
            toggle.click()
            assert toggle.get_attribute("aria-expanded") == "true"
            assert popover.get_attribute("hidden") is None
            assert page.locator("#precisionSessionCalendar .has-results").count() == 1
            assert page.locator("#precisionSessionCalendar .is-empty").count() >= 1
            assert page.locator(".precision-session-date-presets").all_inner_texts()[0].split() == [
                "近3日", "近5日", "周", "月", "季度", "半年", "年"
            ]
            result_day = page.locator("#precisionSessionCalendar .has-results")
            result_day.focus()
            original_date = result_day.get_attribute("data-date")
            page.keyboard.press("ArrowRight")
            assert page.locator(":focus").get_attribute("data-date") != original_date
            page.keyboard.press("Escape")
            assert toggle.get_attribute("aria-expanded") == "false"
            assert page.evaluate("document.activeElement.id") == "precisionSessionDateToggle"
            toggle.click()
            page.locator("[data-date-range='3d']").evaluate("el => el.click()")
            assert page.locator("#precisionSessionDateFrom").input_value()
            assert page.locator("#precisionSessionDateTo").input_value()
            page.locator("#btnPrecisionSessionDateClear").evaluate("el => el.click()")
            assert page.locator("#precisionSessionDateFrom").input_value() == ""
            assert page.locator("#precisionSessionDateTo").input_value() == ""
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
            browser = playwright.chromium.launch(headless=True)
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
            assert "本地选择" in menu.inner_text()
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
            browser = playwright.chromium.launch(headless=os.environ.get("GENBOX_HEADED") != "1")
            page = browser.new_page(viewport={"width": 390, "height": 844})
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
                canvas = page.locator("#precisionAnnotationCanvas")
                canvas.scroll_into_view_if_needed()
                box = canvas.bounding_box()
                assert box
                point = {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}
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

                page.evaluate("setPrecisionEditTool('brush')")
                object_count = page.evaluate("window.precisionEditObjects.length")
                page.mouse.dblclick(point["x"], point["y"], button="left", delay=20)
                page.wait_for_function("!document.querySelector('#precisionImageFullscreen').classList.contains('hidden')")
                assert page.evaluate("window.precisionEditObjects.length") == object_count
                assert page.locator("#precisionImageFullscreenImg").get_attribute("src").startswith("data:image/svg+xml")
                assert page.evaluate("document.fullscreenElement") is None
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
