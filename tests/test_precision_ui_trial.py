from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_trial_projects_controls_and_restores_original(tmp_path):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content("""
          <div id="panelPrecisionEdit"><details id="precisionModelPicker" open>
          <select id="precisionProtocolSelect"><option value="inherit">Auto</option>
          <option value="openai">OpenAI</option></select>
          <select id="precisionResizePreset"><option value="1024x1024">1K square</option>
          <option value="2752x1536">2K landscape</option></select>
          <button id="btnPrecisionAuthorizeModel">Enable</button>
          <button id="btnPrecisionRevokeModel" hidden>Disable</button>
          <button id="btnPrecisionProtocolReset">Reset</button>
          <label for="precisionResizePromptPreset"><span data-i18n="test">Old title</span>
          <select id="precisionResizePromptPreset"><option value="">Choose</option>
          <option value="wide">Expand background</option></select></label>
          <textarea id="precisionResizePrompt"></textarea>
          <section id="precisionTaskMonitor" class="precision-task-idle">
          <span class="precision-task-heading-icon">original</span></section>
          </details></div>
        """)
        page.add_style_tag(path=str(ROOT / "static/css/precision-ui-trial.css"))
        page.evaluate("""() => {
          window.calls = 0;
          document.getElementById('btnPrecisionAuthorizeModel').onclick = () => {
            window.calls++;
          };
          document.getElementById('precisionResizePromptPreset').onchange = e => {
            document.getElementById('precisionResizePrompt').value = 'Expand background';
            e.target.value = '';
          };
        }""")
        page.add_script_tag(path=str(ROOT / "static/js/precision-ui-trial.js"))
        page.get_by_text("原版界面 · 试用新版").click()
        page.locator('.precision-trial-options.size button').nth(1).click()
        assert page.locator('#precisionResizePreset').input_value() == "2752x1536"
        page.get_by_role('switch').click()
        assert page.evaluate("window.calls") == 1
        # No optimistic authorization: only the original handler owns state.
        assert page.get_by_role('switch').get_attribute('aria-checked') == 'false'
        page.evaluate("""() => {
          document.getElementById('btnPrecisionRevokeModel').hidden = false;
          document.getElementById('btnPrecisionAuthorizeModel').hidden = true;
        }""")
        from playwright.sync_api import expect
        expect(page.get_by_role('switch')).to_have_attribute('aria-checked', 'true')
        page.get_by_role('button', name='Expand background', exact=True).click()
        expect(page.get_by_role('button', name='Expand background', exact=True)).to_have_attribute('aria-pressed', 'true')
        assert page.locator('.composition button[data-value=""]').count() == 0
        page.locator('#precisionResizePrompt').fill('Custom composition')
        expect(page.get_by_role('button', name='Expand background', exact=True)).to_have_attribute('aria-pressed', 'false')
        for state in ('failed', 'active', 'completed', 'idle'):
            page.evaluate("(state) => document.getElementById('precisionTaskMonitor').className = 'precision-task-' + state", state)
            expected = {'failed': 'failed', 'active': 'active', 'completed': 'success'}.get(state)
            if expected:
                expect(page.locator('#precisionTaskMonitor')).to_have_class(
                    __import__('re').compile('precision-trial-progress-' + expected))
            else:
                expect(page.locator('#precisionTaskMonitor')).not_to_have_class(
                    __import__('re').compile('precision-trial-progress-'))
        for width in (390, 1394):
            page.set_viewport_size({"width": width, "height": 920})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / f"trial-{width}.png"))
        page.get_by_text("实验界面 · 切回原版").click()
        assert page.locator('#precisionResizePreset').is_visible()
        assert page.locator('#precisionResizePreset').input_value() == "2752x1536"
        assert not page.locator('.precision-trial-command').is_visible()
        assert page.locator('.precision-task-heading-icon').inner_text() == 'original'
        browser.close()
