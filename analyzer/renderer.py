import asyncio
import threading
import time

from playwright.async_api import async_playwright

GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
NORMAL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def _render_async(url: str, use_googlebot: bool, wait_ms: int) -> dict:
    ua = GOOGLEBOT_UA if use_googlebot else NORMAL_UA
    js_resources: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        def on_request(req):
            if req.resource_type == "script":
                js_resources.append(req.url)

        page.on("request", on_request)

        start = time.time()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception:
            # Fallback: wait for domcontentloaded if networkidle times out
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            except Exception as e:
                await browser.close()
                return {"error": str(e)}

        await page.wait_for_timeout(wait_ms)
        render_time = round(time.time() - start, 2)

        html = await page.content()
        screenshot_bytes = await page.screenshot(full_page=True, type="png")

        await browser.close()

    return {
        "html": html,
        "render_time": render_time,
        "screenshot": screenshot_bytes,
        "js_resources": js_resources,
        "js_resource_count": len(js_resources),
    }


def render_page(url: str, use_googlebot: bool = False, wait_ms: int = 3000) -> dict:
    """Run Playwright in a dedicated thread to avoid event loop conflicts with Streamlit."""
    result_box: list = [None]
    error_box: list = [None]

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_box[0] = loop.run_until_complete(_render_async(url, use_googlebot, wait_ms))
        except Exception as exc:
            error_box[0] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=90)

    if error_box[0]:
        raise error_box[0]
    if result_box[0] is None:
        return {"error": "Render timed out after 90 seconds"}
    return result_box[0]
