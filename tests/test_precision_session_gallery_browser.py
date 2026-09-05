from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
            assert toggle.get_attribute("aria-expanded") == "false"
            assert popover.get_attribute("hidden") is not None
            # The static fixture keeps the precision panel hidden; invoke the
            # native handler without coupling this focused test to navigation
            # shell visibility.
            toggle.evaluate("el => el.click()")
            assert toggle.get_attribute("aria-expanded") == "true"
            assert popover.get_attribute("hidden") is None
            assert page.locator("#precisionSessionCalendar .has-results").count() == 1
            assert page.locator("#precisionSessionCalendar .is-empty").count() >= 1
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
