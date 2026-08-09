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
            synthetic_value = f"synthetic-{field_id}"
            if field.is_editable():
                field.fill(synthetic_value)
            else:
                # Saved Push fields are deliberately view/copy-only in the
                # generic credential editor; populate them as the API would.
                field.evaluate("(node, value) => { node.value = value }", synthetic_value)
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


def test_open_close_reopen_rehides_secrets_and_preserves_unedited_private_key():
    credential = {
        "admin_key": "synthetic-admin-key",
        "ssh_password": "synthetic-ssh-password",
        "ssh_private_key": "synthetic private key",
        "ssh_passphrase": "synthetic-passphrase",
        "sudo_password": "synthetic-sudo-password",
        "password": "synthetic-password",
        "api_key": "synthetic-api-key",
        "genbox_push_key": "",
    }
    saved_bodies = []

    def fulfill_api(route):
        path = route.request.url.split("/api/", 1)[-1].split("?", 1)[0]
        if path == "extensions/vault/status":
            route.fulfill(json={"configured": True, "unlocked": True, "entry_count": 1})
        elif path == "extensions/vault/credentials":
            route.fulfill(json={"credentials": [{"instance_handle": "credential-test"}]})
        elif path == "extensions/vault/credentials/credential-test":
            if route.request.method == "PUT":
                saved_bodies.append(route.request.post_data_json)
            route.fulfill(json={"credential": credential})
        elif path == "extensions/instances":
            route.fulfill(json={"instances": []})
        else:
            route.fulfill(json={"targets": [], "categories": [], "items": [], "target_ids": []})

    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/api/**", fulfill_api)
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        page.evaluate("() => window.extensionLoadServices()")

        page.evaluate("() => window.extensionOpenCredential('credential-test')")
        page.locator("#extCredentialModal:not(.hidden)").wait_for()
        private_key = page.locator("#extCredentialSshPrivateKey")
        private_toggle = page.locator("button[onclick*=extCredentialSshPrivateKey]")
        assert private_key.input_value() != credential["ssh_private_key"]
        assert private_key.is_editable() is False
        private_toggle.click()
        assert private_key.input_value() == credential["ssh_private_key"]
        private_toggle.click()
        page.evaluate("() => window.extensionSaveCredential()")
        assert "hidden" in (page.locator("#extCredentialModal").get_attribute("class") or "")
        assert saved_bodies[-1]["credential"]["ssh_private_key"] == credential["ssh_private_key"]

        page.evaluate("() => window.extensionOpenCredential('credential-test')")
        page.locator("#extCredentialModal:not(.hidden)").wait_for()
        for field_id in (
            "extCredentialAdminKey",
            "extCredentialSshPassword",
            "extCredentialSshPassphrase",
            "extCredentialSudoPassword",
            "extCredentialPassword",
            "extCredentialApiKey",
            "extCredentialGenboxPushKey",
        ):
            assert page.locator(f"#{field_id}").get_attribute("type") == "password"
        assert "is-masked" in (private_key.get_attribute("class") or "")
        assert private_key.is_editable() is False
        browser.close()
