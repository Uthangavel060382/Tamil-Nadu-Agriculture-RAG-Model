"""Extract rendered webpage text and links using Playwright."""
import asyncio

from playwright.async_api import Error, TimeoutError, async_playwright


async def scrape_page(url: str, timeout: int = 60, retries: int = 1, *, headless: bool = True):
    if timeout <= 0 or retries < 0:
        raise ValueError("timeout must be positive and retries nonnegative")
    timeout_ms = timeout * 1000
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            for attempt in range(retries + 1):
                page = await browser.new_page()
                try:
                    print(f"Opening: {url} (attempt {attempt + 1}/{retries + 1})")
                    response = await page.goto(
                        url, wait_until="domcontentloaded", timeout=timeout_ms
                    )
                    if response is None:
                        raise RuntimeError(f"No HTTP response from {url}")
                    status = response.status
                    if status >= 400:
                        if status in (408, 429, 500, 502, 503, 504) and attempt < retries:
                            await asyncio.sleep(min(2 ** attempt, 5))
                            continue
                        raise RuntimeError(f"Server returned HTTP {status} for {url}")
                    return {
                        "url": page.url,
                        "status": status,
                        "title": await page.title(),
                        "text": await page.locator("body").inner_text(timeout=timeout_ms),
                        "links": await page.locator("a").evaluate_all(
                            """elements => elements.map(a => ({
                                text: (a.innerText || "").trim(), href: a.href
                            }))"""
                        ),
                    }
                except (TimeoutError, Error) as exc:
                    transient = isinstance(exc, TimeoutError) or any(
                        code in str(exc) for code in (
                            "ERR_CONNECTION_TIMED_OUT", "ERR_CONNECTION_RESET",
                            "ERR_CONNECTION_CLOSED", "ERR_TIMED_OUT",
                        )
                    )
                    if not transient:
                        raise
                    if attempt >= retries:
                        raise RuntimeError(
                            f"Could not load {url} after {retries + 1} attempts "
                            f"with a {timeout}s timeout. Check the site in your browser "
                            "and your network/VPN/proxy; the server may be unavailable."
                        ) from exc
                    print("Temporary connection failure; retrying...")
                    await asyncio.sleep(min(2 ** attempt, 5))
                finally:
                    await page.close()
        finally:
            await browser.close()
