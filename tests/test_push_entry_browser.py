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
global.document={getElementById:element,querySelector(){return null},querySelectorAll(){return []},addEventListener(){},removeEventListener(){},createElement(){return element('created-'+elements.size)},body:{appendChild(){}},execCommand(){return true}};
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
