"""Re-capture sensitive screenshots with masked API info"""
import asyncio, os
from playwright.async_api import async_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanitized")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page = await ctx.new_page()

        await page.goto("http://localhost:8891", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # === Provider Modal ===
        await page.evaluate("switchNav('generate')")
        await page.wait_for_timeout(800)
        await page.evaluate("openProviderModal()")
        await page.wait_for_timeout(1000)

        # Mask API endpoints - replace text in all DIVs containing IP/domain patterns
        await page.evaluate("""() => {
            const els = document.querySelectorAll('#providerModal div');
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent;
                    if (t && (t.match(/\\d+\\.\\d+\\.\\d+/) || t.includes('apihub') || t.includes('/v1'))) {
                        el.textContent = 'provider-name \\u00b7 **.**.**.**:****/v1';
                    }
                }
            }
            // Also mask proxy IP/port fields
            const inputs = document.querySelectorAll('#providerModal input');
            for (const inp of inputs) {
                if (inp.value && (inp.value.match(/\\d+\\.\\d+/) || inp.value.match(/^\\d{4,5}$/))) {
                    inp.value = '***';
                }
            }
        }""")
        await page.wait_for_timeout(300)

        path = os.path.join(OUTPUT_DIR, "12-modal-provider.png")
        await page.screenshot(path=path)
        print(f"Saved: 12-modal-provider.png")

        # === LLM Modal ===
        await page.evaluate("closeProviderModal()")
        await page.wait_for_timeout(500)
        await page.evaluate("openLLMSettings()")
        await page.wait_for_timeout(1000)

        await page.evaluate("""() => {
            const els = document.querySelectorAll('#llmModal div');
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent;
                    if (t && (t.match(/\\d+\\.\\d+\\.\\d+/) || t.includes('apihub') || t.includes('/v1'))) {
                        el.textContent = 'provider \\u00b7 **.**.**.**:****/v1';
                    }
                }
            }
        }""")
        await page.wait_for_timeout(300)

        path = os.path.join(OUTPUT_DIR, "15-modal-llm.png")
        await page.screenshot(path=path)
        print(f"Saved: 15-modal-llm.png")

        # === Dashboard ===
        await page.evaluate("closeLLMModal()")
        await page.wait_for_timeout(500)
        await page.evaluate("switchNav('dashboard')")
        await page.wait_for_timeout(2000)

        # Click the eye button to reveal IP first, then mask it
        await page.evaluate("""() => {
            // Mask IP info panel
            const els = document.querySelectorAll('#pageDashboard div, #pageDashboard span, #pageDashboard td');
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent;
                    if (t && t.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                        el.textContent = '**.**.**.**';
                    }
                    if (t && t.match(/\\d+km/)) {
                        el.textContent = '***km';
                    }
                }
            }
        }""")
        await page.wait_for_timeout(300)

        path = os.path.join(OUTPUT_DIR, "01-dashboard.png")
        await page.screenshot(path=path)
        print(f"Saved: 01-dashboard.png")

        path = os.path.join(OUTPUT_DIR, "16-dashboard-full.png")
        await page.screenshot(path=path, full_page=True)
        print(f"Saved: 16-dashboard-full.png")

        # === Generate page - mask status bar ===
        await page.evaluate("switchNav('generate')")
        await page.wait_for_timeout(800)
        await page.evaluate("""() => {
            const els = document.querySelectorAll('#pageGenerate div, #pageGenerate span');
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent;
                    if (t && t.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                        el.textContent = '**.**.**.**';
                    }
                }
            }
        }""")

        path = os.path.join(OUTPUT_DIR, "02-generate-t2i.png")
        await page.screenshot(path=path)
        print(f"Saved: 02-generate-t2i.png")

        path = os.path.join(OUTPUT_DIR, "17-generate-full.png")
        await page.screenshot(path=path, full_page=True)
        print(f"Saved: 17-generate-full.png")

        # === Video page ===
        await page.evaluate("switchNav('video')")
        await page.wait_for_timeout(800)
        await page.evaluate("""() => {
            const els = document.querySelectorAll('#pageVideo div, #pageVideo span');
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent;
                    if (t && t.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                        el.textContent = '**.**.**.**';
                    }
                }
            }
        }""")

        path = os.path.join(OUTPUT_DIR, "05-video-t2v.png")
        await page.screenshot(path=path)
        print(f"Saved: 05-video-t2v.png")

        path = os.path.join(OUTPUT_DIR, "18-video-full.png")
        await page.screenshot(path=path, full_page=True)
        print(f"Saved: 18-video-full.png")

        await browser.close()
        print("\nDone!")

asyncio.run(main())
