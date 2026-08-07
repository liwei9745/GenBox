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


def test_each_saved_secret_has_independent_show_hide_control():
    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 500})
        page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "test only"}))
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        page.locator("#extCredentialModal").evaluate("node => node.classList.remove('hidden')")
        credential_box = page.locator("#extCredentialModal .ext-credential-box")
        assert credential_box.evaluate("node => getComputedStyle(node).overflowY") == "auto"
        assert credential_box.evaluate("node => node.scrollHeight > node.clientHeight") is True
        credential_box.evaluate("node => { node.scrollTop = node.scrollHeight }")
        page.evaluate(
            """() => {
                window.__credentialActionClicks = [];
                window.extensionCloseCredentialModal = () => window.__credentialActionClicks.push('cancel');
                window.extensionDeleteCredential = () => window.__credentialActionClicks.push('delete');
                window.extensionSaveCredential = () => window.__credentialActionClicks.push('save');
            }"""
        )
        actions = page.locator("#extCredentialModal .ext-reset-actions button")
        assert actions.count() == 3
        for index in range(actions.count()):
            action_box = actions.nth(index).bounding_box()
            assert action_box is not None
            assert action_box["y"] >= 0
            assert action_box["y"] + action_box["height"] <= 500
            actions.nth(index).click()
        assert page.evaluate("window.__credentialActionClicks") == ["cancel", "delete", "save"]

        secret_input_ids = (
            "extCredentialAdminKey",
            "extCredentialSshPassword",
            "extCredentialSshPassphrase",
            "extCredentialSudoPassword",
            "extCredentialPassword",
            "extCredentialApiKey",
            "extCredentialGenboxPushKey",
        )
        for field_id in secret_input_ids:
            field = page.locator(f"#{field_id}")
            toggle = page.locator(f"button[onclick*={field_id}]")
            field.fill(f"synthetic-{field_id}")
            assert field.get_attribute("type") == "password"
            toggle.click()
            assert field.get_attribute("type") == "text"
            assert toggle.get_attribute("aria-pressed") == "true"
            for other_id in secret_input_ids:
                if other_id != field_id:
                    assert page.locator(f"#{other_id}").get_attribute("type") == "password"
            toggle.click()
            assert field.get_attribute("type") == "password"
            assert toggle.get_attribute("aria-pressed") == "false"

        private_key = page.locator("#extCredentialSshPrivateKey")
        private_toggle = page.locator("button[onclick*=extCredentialSshPrivateKey]")
        assert "is-masked" in (private_key.get_attribute("class") or "")
        assert private_key.is_editable() is False
        private_toggle.click()
        assert "is-masked" not in (private_key.get_attribute("class") or "")
        assert private_key.is_editable() is True
        private_key.fill("synthetic replacement private key")
        assert page.locator("#extCredentialGenboxPushKey").get_attribute("type") == "password"
        private_toggle.click()
        assert "is-masked" in (private_key.get_attribute("class") or "")
        assert private_key.is_editable() is False
        assert "synthetic replacement private key" not in private_key.input_value()
        private_toggle.click()
        assert private_key.input_value() == "synthetic replacement private key"
        browser.close()
