import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]


@contextmanager
def _static_site():
    class QuietStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietStaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_dock_lock_survives_navigation_reload_and_unlock_restores_auto_hide():
    """The visible lock is persistent; the bottom handle remains temporary."""
    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 500})
        page.route(
            "**/api/**",
            lambda route: route.fulfill(status=404, json={"detail": "static dock test"}),
        )
        page.goto(f"{base_url}/static/index.html#/dashboard", wait_until="domcontentloaded")

        dock = page.locator("#macDock")
        pin = page.locator("#dockPinButton")
        handle = page.locator("#dockRevealHandle")
        page.evaluate("() => { localStorage.removeItem('igs_dock_pinned'); revealDock(); }")

        assert page.locator("body").evaluate("node => node.classList.contains('dock-auto-hide')")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")
        assert pin.get_attribute("aria-pressed") == "false"
        assert pin.is_visible()
        page.wait_for_timeout(400)

        # A user click enables the persistent lock and keeps the dock visible.
        pin.dispatch_event("click")
        assert pin.get_attribute("aria-pressed") == "true"
        assert page.locator("body").evaluate("node => node.classList.contains('dock-pinned')")
        assert page.evaluate("() => localStorage.getItem('igs_dock_pinned')") == "1"
        page.wait_for_timeout(250)
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        # Page navigation must not reset the user's lock preference.
        page.evaluate("() => switchNav('gallery', document.getElementById('navGallery'))")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-pinned')")
        assert pin.get_attribute("aria-pressed") == "true"

        # Reload restores the preference without any secret-bearing storage.
        page.reload(wait_until="domcontentloaded")
        page.evaluate("() => revealDock()")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-pinned')")
        assert pin.get_attribute("aria-pressed") == "true"
        assert page.evaluate("() => Object.keys(localStorage).filter(key => key.includes('key') || key.includes('token')).length") == 0

        # Unlocking returns to auto-hide; the handle can reveal temporarily.
        pin.dispatch_event("click")
        assert pin.get_attribute("aria-pressed") == "false"
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-pinned')")
        page.evaluate("() => revealDock()")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")
        handle.click()
        page.wait_for_timeout(250)
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        # Keyboard activation is equivalent to a pointer click.
        page.evaluate("() => revealDock()")
        pin.focus()
        page.keyboard.press("Enter")
        assert pin.get_attribute("aria-pressed") == "true"

        # The additional control must fit in a narrow viewport without overflow.
        dock_box = dock.bounding_box()
        assert dock_box is not None
        assert dock_box["x"] >= 0
        assert dock_box["x"] + dock_box["width"] <= 360
        assert page.evaluate("() => document.documentElement.scrollWidth <= 360")
        browser.close()
