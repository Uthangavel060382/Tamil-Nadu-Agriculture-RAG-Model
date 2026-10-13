import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from playwright.async_api import Error, TimeoutError

from ingestion.crawler import scrape_page


class CrawlerTests(unittest.IsolatedAsyncioTestCase):
    def make_browser(self, outcomes):
        pages = []
        for outcome in outcomes:
            page = MagicMock()
            page.goto = AsyncMock(
                side_effect=outcome if isinstance(outcome, Exception) else None,
                return_value=SimpleNamespace(status=outcome),
            )
            page.title = AsyncMock(return_value="Agriculture")
            page.url = "https://example.test/final"
            body = SimpleNamespace(inner_text=AsyncMock(return_value="Soil card information"))
            anchors = SimpleNamespace(evaluate_all=AsyncMock(return_value=[]))
            page.locator.side_effect = lambda selector, body=body, anchors=anchors: body if selector == "body" else anchors
            page.close = AsyncMock()
            pages.append(page)
        browser = SimpleNamespace(new_page=AsyncMock(side_effect=pages), close=AsyncMock())
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=SimpleNamespace(
            chromium=SimpleNamespace(launch=AsyncMock(return_value=browser))
        ))
        context.__aexit__ = AsyncMock(return_value=False)
        return context, browser, pages

    async def check(self, outcomes, *, failure=False):
        context, browser, pages = self.make_browser(outcomes)
        with patch("ingestion.crawler.async_playwright", return_value=context):
            with patch("ingestion.crawler.asyncio.sleep", new=AsyncMock()):
                if failure:
                    with self.assertRaises((RuntimeError, Error)):
                        await scrape_page("https://example.test", retries=len(outcomes) - 1)
                    result = None
                else:
                    result = await scrape_page("https://example.test", retries=len(outcomes) - 1)
        browser.close.assert_awaited_once()
        for page in pages:
            page.close.assert_awaited_once()
        return result

    async def test_success_contract(self):
        result = await self.check([200])
        self.assertEqual(result["text"], "Soil card information")
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["url"], "https://example.test/final")
        self.assertEqual(result["links"], [])

    async def test_connection_timeout_retries(self):
        await self.check([Error("net::ERR_CONNECTION_TIMED_OUT"), 200])

    async def test_http_retry_and_recovery(self):
        await self.check([503, 200])

    async def test_timeout_exhaustion_closes_every_page(self):
        await self.check([TimeoutError("timeout"), TimeoutError("timeout")], failure=True)

    async def test_http_error_is_not_ingested(self):
        await self.check([404], failure=True)

    async def test_invalid_options(self):
        with self.assertRaises(ValueError):
            await scrape_page("https://example.test", timeout=0)


if __name__ == "__main__":
    unittest.main()
