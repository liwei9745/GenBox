import subprocess
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


def _sources():
    return (
        (ROOT / "static" / "index.html").read_text(encoding="utf-8"),
        (ROOT / "static" / "js" / "extensions.js").read_text(encoding="utf-8"),
    )


def _function_body(source: str, marker: str, next_marker: str) -> str:
    return source.split(marker, 1)[1].split(next_marker, 1)[0]


def test_deployed_card_push_entry_has_visible_instance_bound_modal_contract():
    html, js = _sources()

    assert 'id="extPushConfigModal"' in html
    assert 'aria-labelledby="extPushConfigTitle"' in html
    assert 'id="extPushConfigTitle"' in html
    assert "GenBox Push 配置</h3>" in html
    assert 'id="extPushConfigInstance"' in html
    assert 'id="extPushConfigBody"' in html
    for state_id in (
        "extPushConfiguredState",
        "extPushValidityState",
        "extPushLocalState",
        "extPushRemoteAuthState",
    ):
        assert f'id="{state_id}"' in html

    card_block = js.split("extRenderServiceGroups=function", 1)[1]
    assert "data-instance-handle" in card_block
    assert "extensionOpenExistingPushSource(handle)" in js

    open_body = _function_body(
        js,
        "window.extensionOpenPushConfiguration=async function",
        "window.extensionClosePushConfiguration",
    )
    assert "instance_handle:String(handle)" in open_body
    assert "extPushConfigModal" in open_body
    assert "classList.remove('hidden')" in open_body
    assert "extensionPreparePushSource" in open_body

    # Opening an already deployed card must not route through the hidden
    # deployment wizard or close the service drawer as a side effect.
    existing_entry = _function_body(
        js,
        "window.extensionOpenExistingPushSource=async function",
        "window.extensionRevokePushSource",
    )
    assert "extensionCloseDrawer()" not in open_body + existing_entry
    assert "extensionNext(5)" not in open_body + existing_entry
    for forbidden in (
        "extensionStartNewIsolatedDeployment",
        "extensionDeploy",
        "/api/extensions/deploy",
        "cleanup",
    ):
        assert forbidden not in open_body + existing_entry

    status_body = _function_body(
        js,
        "function setPushSourceAccess",
        "async function resolvePushSourceHandle",
    )
    assert "data&&data.revoked" in status_body
    assert "extensions.push_state_revoked" in status_body
    assert "extensions.push_state_auth_unverified" in status_body
    assert "push_state_active" not in status_body


def test_push_modal_close_returns_to_deployed_services_drawer():
    _html, js = _sources()
    close_body = _function_body(
        js,
        "window.extensionClosePushConfiguration=function",
        "window.extensionPreparePushSource",
    )

    assert "extPushConfigModal" in close_body
    assert "classList.add('hidden')" in close_body
    assert "extensionOpenDrawer()" in close_body


def test_push_entry_keeps_key_and_confirmation_out_of_public_card_and_url():
    html, js = _sources()
    card_block = js.split("extRenderServiceGroups=function", 1)[1]
    # Public service cards may expose only the opaque handle and non-secret
    # access metadata; the raw Push key must remain in the modal flow.
    card_until_renderer_end = card_block.split("// The service-card renderer", 1)[0]
    assert "push_key" not in card_until_renderer_end
    assert "confirmation_token" not in card_until_renderer_end
    assert "localStorage" not in card_until_renderer_end
    assert "sessionStorage" not in card_until_renderer_end

    open_body = _function_body(
        js,
        "window.extensionOpenPushConfiguration=async function",
        "window.extensionClosePushConfiguration",
    )
    assert "encodeURIComponent(handle)" in open_body or "instance_handle" in open_body
    assert "push_key" not in open_body
    assert "confirmation_token" not in open_body
    assert "localStorage" not in open_body
    assert "sessionStorage" not in open_body

    # The visible title must be product text, not a translation key marker.
    assert "GenBox Push 配置" in html
    assert "extensions.push_source_title" in html


def test_browser_click_opens_modal_for_the_card_handle_and_close_restores_drawer():
    """Run the real browser entry functions against a small DOM harness."""
    source = ROOT / "static" / "js" / "extensions.js"
    node = r'''
const fs=require('fs');const source=fs.readFileSync(process.argv[1],'utf8');
global.window=global;
const elements=new Map();
function classes(){const values=new Set(['hidden']);return {add:n=>values.add(n),remove:n=>values.delete(n),toggle:(n,on)=>on?values.add(n):values.delete(n),contains:n=>values.has(n)}}
function element(id){
  if(!elements.has(id)){
    const item={id,value:'',textContent:'',innerHTML:'',disabled:false,checked:false,type:'text',dataset:{},classList:classes(),
      parentNode:null,nextSibling:null,style:{},setAttribute(){},removeAttribute(){},focus(){},select(){},remove(){},
      querySelector(){return null},querySelectorAll(){return []},closest(){return null}};
    item.appendChild=child=>{child.parentNode=item;child.nextSibling=null;return child};
    item.insertBefore=(child,next)=>{child.parentNode=item;child.nextSibling=next||null;return child};
    elements.set(id,item);
  }
  return elements.get(id);
}
const page=element('wizard-parent'),body=element('extPushConfigBody'),sourcePanel=element('extPushSource');
page.appendChild(sourcePanel);
global.document={getElementById:element,querySelector(){return null},querySelectorAll(){return []},addEventListener(){},removeEventListener(){},createElement(){return element('created-'+elements.size)},body:element('document-body'),execCommand(){return true}};
global.i18nText=key=>key;global.escHtml=value=>String(value||'');global.confirm=()=>true;global.getUiLanguage=()=> 'zh-CN';
global._authFetch=async()=>{throw new Error('opening the existing card must not call an unrelated endpoint')};
eval(source);
let prepareCalls=0,drawerCalls=0,drawerClosed=0;
window.extensionPreparePushSource=async()=>{prepareCalls+=1};
window.extensionOpenDrawer=()=>{drawerCalls+=1};
window.extensionCloseDrawer=()=>{drawerClosed+=1};
(async()=>{
  const handle='opaque-card-handle';
  await window.extensionOpenExistingPushSource(handle);
  if(element('extPushConfigModal').classList.contains('hidden'))throw new Error('card click did not make Push modal visible');
  if(sourcePanel.parentNode!==body)throw new Error('Push controls were not moved into visible modal body');
  if(!element('extPushConfigInstance').textContent.includes(handle))throw new Error('modal did not bind the selected opaque handle');
  if(prepareCalls!==1)throw new Error('card click did not load current Push configuration exactly once');
  if(drawerClosed!==0)throw new Error('card click closed the deployed services drawer');
  window.extensionClosePushConfiguration();
  if(!element('extPushConfigModal').classList.contains('hidden'))throw new Error('close left Push modal visible');
  if(sourcePanel.parentNode!==page)throw new Error('close did not restore Push controls to their original page');
  if(drawerCalls!==1)throw new Error('close did not return to deployed services drawer');
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result = subprocess.run(["node", "-e", node, str(source)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_playwright_click_on_deployed_card_opens_push_modal_and_returns_to_drawer():
    """Exercise the entry through a genuine local browser click, with APIs mocked."""
    instance_handle = "opaque-card-handle"
    observed_api_urls = []

    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        def mock_extension_api(route):
            request = route.request
            path = request.url.split("/api/", 1)[-1]
            observed_api_urls.append(request.url)
            if path == "setup/status":
                route.fulfill(json={
                    "app_mode": "prod",
                    "auth_required": False,
                    "needs_provider_setup": False,
                })
            elif path == "runtime/status":
                route.fulfill(json={
                    "service": "genbox",
                    "version": "test",
                    "mode": "dev",
                    "port": 8892,
                    "runtime_id": "local-playwright-test",
                })
            elif path == "extensions/instances":
                route.fulfill(json={
                    "instances": [{
                        "handle": instance_handle,
                        "project": "chatgpt2api",
                        "managed": True,
                        "running": True,
                        "console_url": "https://console.invalid",
                        "api_url": "https://console.invalid/v1",
                    }],
                })
            elif path == f"extensions/push-sources/{instance_handle}":
                route.fulfill(json={
                    "configured": False,
                    "destination_url": "https://genbox.invalid/api/sync/push",
                })
            elif path == "extensions/vault/status":
                route.fulfill(json={"configured": False, "unlocked": False, "entry_count": 0})
            else:
                # No mocked request has side effects. Unexpected extension API
                # calls fail locally rather than escaping to a backend.
                route.fulfill(status=404, json={"detail": "test mock only"})

        page.route("**/api/**", mock_extension_api)
        try:
            page.goto(f"{base_url}/static/index.html", wait_until="networkidle")
            page.locator("#navExtensions").click()
            page.locator("#pageExtensions").wait_for(state="visible")

            page.locator("#extFab").click()
            manage_push = page.get_by_role("button", name="管理 Push 配置")
            manage_push.wait_for(state="visible")
            manage_push.click()

            modal = page.locator("#extPushConfigModal")
            assert modal.is_visible()
            # The managed-card action must stay on the extensions surface and
            # keep the deployed-services drawer open; returning to the hidden
            # deployment wizard is the regression this test is guarding.
            assert page.locator("#pageExtensions").is_visible()
            assert "ext-drawer-open" in (page.locator("#extDrawer").get_attribute("class") or "")
            assert modal.locator("#extPushConfigTitle").text_content() == "GenBox Push 配置"
            assert instance_handle in (modal.locator("#extPushConfigInstance").text_content() or "")
            assert modal.locator("#extPushSource").is_visible()
            assert page.locator("#extPushCreateBtn").is_visible()
            assert not page.locator("#extPushSaveBtn").is_visible()

            page.keyboard.press("Escape")
            assert not modal.is_visible()
            assert "ext-drawer-open" in (page.locator("#extDrawer").get_attribute("class") or "")

            manage_push.click()
            assert modal.is_visible()
            modal.locator(".ext-modal-close").click()
            assert not modal.is_visible()
            assert "ext-drawer-open" in (page.locator("#extDrawer").get_attribute("class") or "")

            assert not any("deploy" in url or "cleanup" in url for url in observed_api_urls)
            assert not any("push_key=" in url or "confirmation_token=" in url for url in observed_api_urls)
        finally:
            browser.close()


def test_both_push_configuration_copy_actions_use_real_line_breaks():
    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/api/**", lambda route: route.fulfill(status=404, json={"detail": "copy test"}))
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        copied = page.evaluate(
            """async () => {
                const writes = [];
                Object.defineProperty(navigator, 'clipboard', {
                    configurable: true,
                    value: {writeText: async value => writes.push(value)},
                });
                document.getElementById('extPushDestinationUrl').value = 'https://loopback.invalid/api/sync/push';
                document.getElementById('extPushSourceId').value = 'synthetic-source';
                document.getElementById('extPushKey').value = 'synthetic-push-key';
                await window.extensionCopyPushConfiguration();
                document.getElementById('extCredentialGenboxPushUrl').value = 'https://loopback.invalid/api/sync/push';
                document.getElementById('extCredentialGenboxPushSourceId').value = 'synthetic-source';
                document.getElementById('extCredentialGenboxPushKey').value = 'synthetic-push-key';
                await window.extensionCopySavedPushConfiguration();
                return writes;
            }"""
        )

        assert len(copied) == 2
        for value in copied:
            assert value.splitlines() == [
                "GenBox Push URL: https://loopback.invalid/api/sync/push",
                "Source ID: synthetic-source",
                "Push Key: synthetic-push-key",
            ]
            assert "\\n" not in value
            assert value.count("\n") == 2
        browser.close()


def test_push_save_uses_in_app_confirmation_and_renders_honest_status_on_narrow_screen():
    instance_handle = "synthetic-managed-instance"
    source_id = "synthetic-source-id"
    push_key = "synthetic-browser-only-key"
    confirmation_token = "synthetic-one-time-confirmation"
    mutating_requests = []
    saved_locally = False

    def fulfill_api(route):
        nonlocal saved_locally
        request = route.request
        path = request.url.split("/api/", 1)[-1].split("?", 1)[0]
        method = request.method
        if path == "setup/status":
            route.fulfill(json={"app_mode": "prod", "auth_required": False, "needs_provider_setup": False})
        elif path == "runtime/status":
            route.fulfill(json={
                "service": "genbox",
                "version": "test",
                "mode": "dev",
                "port": 0,
                "runtime_id": "loopback-browser-test",
            })
        elif path == "extensions/instances":
            route.fulfill(json={"instances": [{
                "handle": instance_handle,
                "project": "chatgpt2api",
                "managed": True,
                "running": True,
            }]})
        elif path == f"extensions/push-sources/{instance_handle}" and method == "GET":
            route.fulfill(json={
                "configured": False,
                "source": None,
                "saved_locally": False,
                "destination_url": "https://loopback.invalid/api/sync/push",
            })
        elif path == "extensions/push-sources" and method == "POST":
            mutating_requests.append((method, path))
            route.fulfill(json={
                "configured": True,
                "source": {"source_id": source_id},
                "saved_locally": False,
                "destination_url": "https://loopback.invalid/api/sync/push",
                "push_key": push_key,
            })
        elif path == "extensions/vault/status":
            route.fulfill(json={"configured": True, "unlocked": True, "entry_count": int(saved_locally)})
        elif path == "extensions/vault/credentials":
            route.fulfill(json={"credentials": []})
        elif path == f"extensions/vault/credentials/{instance_handle}" and method == "GET":
            route.fulfill(json={"credential": {}})
        elif path == f"extensions/vault/credentials/{instance_handle}/push-key/confirmation":
            mutating_requests.append((method, path))
            body = request.post_data_json
            assert body == {"source_id": source_id, "push_key": push_key}
            route.fulfill(json={"confirmation_token": confirmation_token, "expires_in_seconds": 120})
        elif path == f"extensions/vault/credentials/{instance_handle}/push-key":
            mutating_requests.append((method, path))
            body = request.post_data_json
            assert body == {
                "source_id": source_id,
                "destination_url": "https://loopback.invalid/api/sync/push",
                "push_key": push_key,
                "confirmation_token": confirmation_token,
                "save_push_key_locally": True,
            }
            saved_locally = True
            route.fulfill(json={"saved_locally": True, "remote_unchanged": True})
        else:
            route.fulfill(status=404, json={"detail": "local browser mock only"})

    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 500})
        native_dialogs = []

        def reject_native_dialog(dialog):
            native_dialogs.append(dialog.type)
            dialog.dismiss()

        page.on("dialog", reject_native_dialog)
        page.route("**/api/**", fulfill_api)
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        page.evaluate(f"() => window.extensionOpenExistingPushSource('{instance_handle}')")

        modal = page.locator("#extPushConfigModal")
        modal.wait_for(state="visible")
        box = modal.locator(".ext-push-config-box")
        assert box.evaluate("node => ['auto', 'scroll'].includes(getComputedStyle(node).overflowY)")
        assert box.bounding_box()["height"] <= 500
        assert "extensions." not in modal.inner_text()

        checkbox = page.locator("#extPushSaveOptIn")
        choice = page.locator("label.extension-push-save-choice", has=checkbox)
        assert checkbox.is_checked() is False
        assert checkbox.is_disabled() is True
        assert choice.is_visible()
        assert page.locator("#extPushDeleteLocalBtn").is_hidden()
        checkbox_box = checkbox.bounding_box()
        assert checkbox_box is not None
        assert checkbox_box["width"] >= 18
        assert checkbox_box["height"] >= 18

        assert "未配置" in page.locator("#extPushConfiguredState").inner_text()
        empty_validity = page.locator("#extPushValidityState").inner_text()
        assert any(label in empty_validity for label in ("暂无来源", "来源不存在", "不存在"))
        assert "未保存" in page.locator("#extPushLocalState").inner_text()
        assert "未验证" in page.locator("#extPushRemoteAuthState").inner_text()
        assert "active" not in modal.inner_text().lower()

        page.locator("#extPushCreateBtn").click()
        page.wait_for_function("() => !document.getElementById('extPushSaveOptIn').disabled")
        assert checkbox.is_disabled() is False
        assert checkbox.is_checked() is False
        assert "已配置" in page.locator("#extPushConfiguredState").inner_text()
        assert "未撤销" in page.locator("#extPushValidityState").inner_text()
        assert "未保存" in page.locator("#extPushLocalState").inner_text()
        assert "未验证" in page.locator("#extPushRemoteAuthState").inner_text()
        choice.click()
        assert checkbox.is_checked() is True

        save_button = page.locator("#extPushSaveBtn")
        save_button.scroll_into_view_if_needed()
        button_box = save_button.bounding_box()
        assert button_box is not None
        assert 0 <= button_box["y"] < 500
        save_button.click()

        confirm_modal = page.locator("#extPushSaveConfirmModal")
        assert confirm_modal.is_visible()
        assert native_dialogs == []
        assert not any(path.endswith("/confirmation") or path.endswith("/push-key") for _, path in mutating_requests)
        page.locator("#extPushSaveConfirmCancelBtn").click()
        assert not confirm_modal.is_visible()
        assert page.locator("#extPushKey").input_value() == push_key
        assert not any(path.endswith("/confirmation") or path.endswith("/push-key") for _, path in mutating_requests)

        save_button.click()
        assert confirm_modal.is_visible()
        page.locator("#extPushSaveConfirmBtn").click()
        page.wait_for_function("() => document.getElementById('extPushKey').value === ''")
        assert native_dialogs == []
        confirmation_calls = [item for item in mutating_requests if item[1].endswith("/confirmation")]
        save_calls = [item for item in mutating_requests if item[1].endswith("/push-key")]
        assert confirmation_calls == [("POST", f"extensions/vault/credentials/{instance_handle}/push-key/confirmation")]
        assert save_calls == [("PUT", f"extensions/vault/credentials/{instance_handle}/push-key")]
        page.wait_for_function(
            "() => !document.getElementById('extPushLocalState').textContent.includes('未保存')"
        )
        saved_state = page.locator("#extPushLocalState").inner_text()
        assert "保存" in saved_state and "未保存" not in saved_state
        assert page.locator("#extPushDeleteLocalBtn").is_visible()
        assert "未验证" in page.locator("#extPushRemoteAuthState").inner_text()

        page.evaluate("() => window.extensionClosePushConfiguration()")
        assert not modal.is_visible()
        page.evaluate(f"() => window.extensionOpenExistingPushSource('{instance_handle}')")
        modal.wait_for(state="visible")
        assert checkbox.is_checked() is False
        assert page.locator("#extPushKey").input_value() == ""
        assert page.locator("#extPushKey").get_attribute("type") == "password"
        assert not confirm_modal.is_visible()
        assert "extensions." not in modal.inner_text()
        browser.close()


def test_delete_local_push_copy_uses_dedicated_route_and_keeps_source_configured():
    instance_handle = "synthetic-managed-delete-instance"
    source_id = "synthetic-source-to-keep"
    saved_locally = True
    mutating_requests = []
    other_credential = {
        "admin_key": "synthetic-admin-key-to-keep",
        "note": "synthetic note to keep",
    }

    def fulfill_api(route):
        nonlocal saved_locally
        request = route.request
        path = request.url.split("/api/", 1)[-1].split("?", 1)[0]
        method = request.method
        if path == "setup/status":
            route.fulfill(json={"app_mode": "prod", "auth_required": False, "needs_provider_setup": False})
        elif path == "runtime/status":
            route.fulfill(json={
                "service": "genbox",
                "version": "test",
                "mode": "dev",
                "port": 0,
                "runtime_id": "loopback-delete-test",
            })
        elif path == "extensions/instances":
            route.fulfill(json={"instances": [{
                "handle": instance_handle,
                "project": "chatgpt2api",
                "managed": True,
                "running": True,
            }]})
        elif path == f"extensions/push-sources/{instance_handle}" and method == "GET":
            route.fulfill(json={
                "configured": True,
                "revoked": False,
                "source": {"source_id": source_id},
                "saved_locally": saved_locally,
                "destination_url": "https://loopback.invalid/api/sync/push",
            })
        elif path == "extensions/vault/status":
            route.fulfill(json={"configured": True, "unlocked": True, "entry_count": 1})
        elif path == "extensions/vault/credentials":
            route.fulfill(json={"credentials": [{
                "instance_handle": instance_handle,
                "fields": ["admin_key", "note"] + ([
                    "genbox_push_key", "genbox_push_source_id", "genbox_push_url"
                ] if saved_locally else []),
            }]})
        elif path == f"extensions/vault/credentials/{instance_handle}" and method == "GET":
            credential = dict(other_credential)
            if saved_locally:
                credential.update({
                    "genbox_push_key": "synthetic-local-copy",
                    "genbox_push_source_id": source_id,
                    "genbox_push_url": "https://loopback.invalid/api/sync/push",
                })
            route.fulfill(json={"credential": credential})
        elif path == f"extensions/vault/credentials/{instance_handle}/push-key" and method == "DELETE":
            mutating_requests.append((method, path))
            assert request.post_data is None
            saved_locally = False
            route.fulfill(json={"deleted": True, "remote_unchanged": True})
        elif path == f"extensions/vault/credentials/{instance_handle}" and method == "DELETE":
            mutating_requests.append((method, path))
            route.fulfill(status=500, json={"detail": "generic credential delete must not be called"})
        else:
            route.fulfill(status=404, json={"detail": "local browser mock only"})

    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 500})
        confirmation_text = []

        def accept_delete_confirmation(dialog):
            confirmation_text.append(dialog.message)
            dialog.accept()

        page.on("dialog", accept_delete_confirmation)
        page.route("**/api/**", fulfill_api)
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        page.evaluate("() => window.setExtensionsBackendOnline(true)")
        page.evaluate("() => window.extensionLoadServices()")
        page.evaluate(f"() => window.extensionOpenExistingPushSource('{instance_handle}')")

        modal = page.locator("#extPushConfigModal")
        modal.wait_for(state="visible")
        delete_button = page.locator("#extPushDeleteLocalBtn")
        delete_button.wait_for(state="visible")
        page.wait_for_function("() => !document.getElementById('extPushDeleteLocalBtn').disabled")
        assert delete_button.is_enabled()
        assert page.locator("#extPushConfiguredState").get_attribute("class") == "ready"
        assert page.locator("#extPushValidityState").get_attribute("class") == "ready"
        assert page.locator("#extPushLocalState").get_attribute("class") == "ready"

        delete_button.scroll_into_view_if_needed()
        delete_button.click()
        page.wait_for_function("() => document.getElementById('extPushDeleteLocalBtn').classList.contains('hidden')")

        assert len(confirmation_text) == 1
        assert "Push Key" in confirmation_text[0]
        assert "远端" in confirmation_text[0]
        assert mutating_requests == [(
            "DELETE",
            f"extensions/vault/credentials/{instance_handle}/push-key",
        )]
        assert other_credential == {
            "admin_key": "synthetic-admin-key-to-keep",
            "note": "synthetic note to keep",
        }
        assert page.locator("#extPushConfiguredState").get_attribute("class") == "ready"
        assert page.locator("#extPushValidityState").get_attribute("class") == "ready"
        assert page.locator("#extPushLocalState").get_attribute("class") == "neutral"
        assert page.locator("#extPushRemoteAuthState").get_attribute("class") == "pending"
        assert "extensions." not in modal.inner_text()
        browser.close()


def test_locked_vault_disables_local_push_key_deletion_with_visible_guidance():
    instance_handle = "synthetic-locked-delete-instance"
    source_id = "synthetic-locked-source"
    mutating_requests = []

    def fulfill_api(route):
        request = route.request
        path = request.url.split("/api/", 1)[-1].split("?", 1)[0]
        if path == "setup/status":
            route.fulfill(json={"app_mode": "prod", "auth_required": False, "needs_provider_setup": False})
        elif path == "runtime/status":
            route.fulfill(json={
                "service": "genbox", "version": "test", "mode": "dev", "port": 0,
                "runtime_id": "loopback-locked-delete-test",
            })
        elif path == "extensions/instances":
            route.fulfill(json={"instances": [{
                "handle": instance_handle, "project": "chatgpt2api", "managed": True,
                "running": True,
            }]})
        elif path == f"extensions/push-sources/{instance_handle}":
            route.fulfill(json={
                "configured": True,
                "revoked": False,
                "source": {"source_id": source_id},
                "saved_locally": True,
                "destination_url": "https://loopback.invalid/api/sync/push",
            })
        elif path == "extensions/vault/status":
            route.fulfill(json={"configured": True, "unlocked": False, "entry_count": 1})
        elif path == "extensions/vault/credentials":
            route.fulfill(json={"credentials": [{
                "instance_handle": instance_handle,
                "fields": ["genbox_push_key", "genbox_push_source_id", "genbox_push_url"],
            }]})
        elif path.endswith("/push-key") and request.method == "DELETE":
            mutating_requests.append((request.method, path))
            route.fulfill(status=500, json={"detail": "locked vault must not delete"})
        else:
            route.fulfill(status=404, json={"detail": "local browser mock only"})

    with _static_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 500})
        page.route("**/api/**", fulfill_api)
        page.goto(f"{base_url}/static/index.html", wait_until="domcontentloaded")
        page.evaluate("() => window.setExtensionsBackendOnline(true)")
        page.evaluate("() => window.extensionLoadServices()")
        page.evaluate(f"() => window.extensionOpenExistingPushSource('{instance_handle}')")

        modal = page.locator("#extPushConfigModal")
        modal.wait_for(state="visible")
        delete_button = page.locator("#extPushDeleteLocalBtn")
        delete_button.wait_for(state="visible")
        assert delete_button.is_enabled() is False
        assert "解锁" in (delete_button.get_attribute("title") or "")
        hint = page.locator("#extPushDeleteLocalHint")
        assert hint.is_visible()
        assert "解锁" in hint.inner_text()

        page.evaluate("() => window.extensionDeleteLocalPushKey()")
        assert mutating_requests == []
        browser.close()
