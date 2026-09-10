"""Local synthetic acceptance for help text and one-time navigation."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[1]


def test_precision_quick_start_once_replay_navigation_and_storage_failure(tmp_path):
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
            mutations = []

            def route_api(route):
                if route.request.method not in ("GET", "HEAD"):
                    mutations.append(route.request.url)
                route.fulfill(status=404, json={"detail": "test only"})

            page.route("**/api/**", route_api)
            url = f"http://127.0.0.1:{server.server_port}/static/index.html"
            page.goto(url, wait_until="networkidle")
            page.evaluate("""() => {
                document.querySelector('#pageDashboard').classList.add('hidden');
                ['#loginPage', '#welcomePage', '#setupWizard', '#onboardingTour'].forEach(selector => {
                    const blocker = document.querySelector(selector);
                    if (blocker) blocker.classList.add('hidden');
                });
                document.querySelector('#pageGenerate').classList.remove('hidden');
                document.querySelector('#pageGenerate').classList.add('precision-workbench');
                document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                ensurePrecisionEditPanel();
                currentMode = 'precision_edit';
                schedulePrecisionQuickStart();
            }""")
            dialog = page.locator("#precisionDocsDialog")
            page.wait_for_timeout(800)
            assert dialog.is_visible(), page.evaluate("""() => ({
                mode: currentMode, page: getVisibleAppPage(),
                panelRects: document.querySelector('#panelPrecisionEdit').getClientRects().length,
                blockers: Array.from(document.querySelectorAll('[aria-modal="true"], .modal-overlay, #setupWizard, #welcomePage, #loginPage, #onboardingTour'))
                    .filter(el => el.getClientRects().length && getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden')
                    .map(el => ({id: el.id, class: el.className}))
            })""")
            dialog.wait_for(state="visible")
            assert page.locator(".precision-quick-navigation li").count() == 5
            assert "在线模型" in page.locator(".precision-smart-start-hint").inner_text()
            assert page.locator(".precision-model-picker-body .precision-start-hint").count() == 1
            assert page.evaluate("() => getComputedStyle(document.querySelector('.precision-size-heading-copy')).textAlign") == "center"
            # Keyboard focus stays within the reused help dialog.
            page.locator("#precisionDocsDone").focus()
            page.keyboard.press("Tab")
            assert page.locator("#btnPrecisionDocsClose").evaluate("el => el === document.activeElement")
            page.keyboard.press("Escape")
            assert not dialog.is_visible()
            assert page.evaluate("() => localStorage.getItem('genbox_precision_quick_start_v1')") == "seen"
            page.evaluate("() => schedulePrecisionQuickStart()")
            page.wait_for_timeout(650)
            assert not dialog.is_visible()
            # Replay is always available and changes only navigation state.
            for area, selector in [
                ("model", "#precisionModelPicker"), ("source", "#precisionCanvasShell"),
                ("size", ".precision-size-tool"), ("generate", "#precisionGalleryCommandBar"),
                ("local", ".precision-quick-tools"),
            ]:
                page.evaluate("() => openPrecisionDocsDialog()")
                page.locator(f'.precision-quick-navigation [onclick="navigatePrecisionQuickStart(\'{area}\')"]').click()
                assert not dialog.is_visible()
                assert page.locator(selector).evaluate("el => el === document.activeElement")
            assert page.locator("#precisionModelPicker").evaluate("el => el.open")
            # A new JS session respects the persisted flag.
            page.reload(wait_until="networkidle")
            page.evaluate("""() => {
                document.querySelector('#pageDashboard').classList.add('hidden');
                ['#loginPage', '#welcomePage', '#setupWizard', '#onboardingTour'].forEach(selector => {
                    const blocker = document.querySelector(selector);
                    if (blocker) blocker.classList.add('hidden');
                });
                document.querySelector('#pageGenerate').classList.remove('hidden');
                document.querySelector('#panelPrecisionEdit').classList.remove('hidden');
                currentMode = 'precision_edit'; schedulePrecisionQuickStart();
            }""")
            page.wait_for_timeout(650)
            assert not dialog.is_visible()
            # Navigation away before the timer fires does not open help elsewhere.
            page.evaluate("""() => {
                localStorage.removeItem('genbox_precision_quick_start_v1');
                precisionQuickStartShown = false;
                cancelPrecisionQuickStart();
                schedulePrecisionQuickStart(); currentMode = 't2i';
            }""")
            page.wait_for_timeout(650)
            assert not dialog.is_visible()
            # Blocked browser storage still allows dismissing once per JS session.
            page.evaluate("""() => {
                cancelPrecisionQuickStart();
                precisionQuickStartShown = false;
                Storage.prototype.getItem = function() { throw new Error('blocked'); };
                Storage.prototype.setItem = function() { throw new Error('blocked'); };
                const blocker = document.createElement('div');
                blocker.id = 'quickStartTestModal';
                blocker.setAttribute('aria-modal', 'true');
                blocker.style.cssText = 'position:fixed;inset:0;z-index:99999;background:white';
                document.body.appendChild(blocker);
                currentMode = 'precision_edit'; schedulePrecisionQuickStart();
            }""")
            page.wait_for_timeout(650)
            assert not dialog.is_visible()
            page.evaluate("() => document.querySelector('#quickStartTestModal').remove()")
            dialog.wait_for(state="visible")
            page.keyboard.press("Escape")
            page.evaluate("() => schedulePrecisionQuickStart()")
            page.wait_for_timeout(650)
            assert not dialog.is_visible()
            for width, height in [(1438, 994), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("() => openPrecisionDocsDialog()")
                assert page.locator("#precisionDocsPanel").evaluate("""el => {
                    const r = el.getBoundingClientRect();
                    return r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight
                        && el.scrollWidth <= el.clientWidth;
                }""")
                page.screenshot(path=str(tmp_path / f"precision-quick-start-{width}.png"))
                page.keyboard.press("Escape")
            assert not mutations
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
