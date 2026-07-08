"""Find provider card subtitle structure"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        await page.goto("http://localhost:8891", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.evaluate("switchNav('generate')")
        await page.wait_for_timeout(800)
        await page.evaluate("openProviderModal()")
        await page.wait_for_timeout(1000)

        # Find elements containing IP addresses
        result = await page.evaluate("""() => {
            const els = document.querySelectorAll('#providerModal *');
            const found = [];
            for (const el of els) {
                if (el.children.length === 0) {
                    const t = el.textContent.trim();
                    if (t.match(/\\d+\\.\\d+\\.\\d+/) || t.includes('apihub') || t.includes('/v1')) {
                        found.push({
                            tag: el.tagName,
                            cls: el.className,
                            text: t.substring(0, 100),
                            parentTag: el.parentElement.tagName,
                            parentCls: el.parentElement.className,
                            gpCls: el.parentElement.parentElement ? el.parentElement.parentElement.className : ''
                        });
                    }
                }
            }
            return found;
        }""")

        for item in result:
            print(f"{item['tag']}.{item['cls']} -> text: {item['text']}")
            print(f"  parent: {item['parentTag']}.{item['parentCls']}")
            print(f"  grandparent: {item['gpCls']}")
            print()

        await browser.close()

asyncio.run(main())
