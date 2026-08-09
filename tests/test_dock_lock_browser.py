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


def test_dock_modes_survive_reload_and_hidden_lock_blocks_reveal_zone():
    """Auto, locked-visible, and locked-hidden are distinct persistent modes."""
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
        page.evaluate(
            """() => {
                localStorage.removeItem('igs_dock_pinned');
                localStorage.removeItem('igs_dock_mode');
                setDockMode('auto');
                revealDock();
            }"""
        )

        assert page.locator("body").evaluate("node => node.classList.contains('dock-auto-hide')")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")
        assert pin.get_attribute("aria-pressed") == "false"
        assert pin.is_visible()
        page.wait_for_timeout(400)

        # First click locks the dock visible.
        pin.dispatch_event("click")
        assert pin.get_attribute("aria-pressed") == "true"
        assert page.locator("body").evaluate("node => node.classList.contains('dock-locked-visible')")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-pinned')")
        assert page.evaluate("() => localStorage.getItem('igs_dock_mode')") == "visible"
        page.wait_for_timeout(250)
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        # Page navigation must not reset the user's lock preference.
        page.evaluate("() => switchNav('gallery', document.getElementById('navGallery'))")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-locked-visible')")
        assert pin.get_attribute("aria-pressed") == "true"

        # Reload restores locked-visible without any secret-bearing storage.
        page.reload(wait_until="domcontentloaded")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-locked-visible')")
        assert pin.get_attribute("aria-pressed") == "true"
        assert page.evaluate("() => Object.keys(localStorage).filter(key => key.includes('key') || key.includes('token')).length") == 0

        # Second click locks the dock hidden. Neither the broad page bottom nor
        # the real center reveal zone may reveal it in this mode.
        pin.dispatch_event("click")
        assert pin.get_attribute("aria-pressed") == "true"
        assert page.locator("body").evaluate("node => node.classList.contains('dock-locked-hidden')")
        assert page.evaluate("() => localStorage.getItem('igs_dock_mode')") == "hidden"
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")
        handle.dispatch_event("click")
        page.locator("body").hover(position={"x": 180, "y": 499})
        page.wait_for_timeout(250)
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        page.reload(wait_until="domcontentloaded")
        assert page.locator("body").evaluate("node => node.classList.contains('dock-locked-hidden')")
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        # Third activation returns to auto-hide. Only the center 40% reveal
        # zone is interactive, so edge hover cannot disturb normal controls.
        pin.focus()
        page.keyboard.press("Enter")
        assert pin.get_attribute("aria-pressed") == "false"
        assert page.evaluate("() => localStorage.getItem('igs_dock_mode')") == "auto"
        page.mouse.move(8, 20)
        page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); hideDockNow(); }")
        zone_box = page.locator("#dockRevealZone").bounding_box()
        assert zone_box is not None
        assert abs(zone_box["x"] - 108) <= 1
        assert abs(zone_box["width"] - 144) <= 2
        page.mouse.move(8, 499)
        page.wait_for_timeout(150)
        assert not page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")
        page.mouse.move(180, 20)
        page.mouse.move(180, 499)
        page.wait_for_timeout(150)
        assert page.locator("body").evaluate("node => node.classList.contains('dock-revealed')")

        # The additional control must fit in a narrow viewport without overflow.
        dock_box = dock.bounding_box()
        assert dock_box is not None
        assert dock_box["x"] >= 0
        assert dock_box["x"] + dock_box["width"] <= 360
        assert page.evaluate("() => document.documentElement.scrollWidth <= 360")
        browser.close()
