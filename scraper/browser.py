import asyncio
import random

from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright


class BrowserManager:
    """Async context manager for a Playwright Chromium browser with anti-detection defaults."""

    BATCH_SIZE = 30

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._profile_count = 0

    async def __aenter__(self) -> "BrowserManager":
        self._playwright = await async_playwright().start()
        await self._launch()
        return self

    async def __aexit__(self, *exc):
        await self._close()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _launch(self):
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-ZA",
        )

    async def _close(self):
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None

    async def new_page(self):
        return await self._context.new_page()

    async def maybe_restart(self):
        """Restart browser session every BATCH_SIZE profiles for anti-detection."""
        self._profile_count += 1
        if self._profile_count % self.BATCH_SIZE == 0:
            await self._close()
            await human_delay(3000, 6000)
            await self._launch()


async def human_delay(min_ms: int = 800, max_ms: int = 2500):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
