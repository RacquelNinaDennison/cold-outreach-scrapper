import json
import os
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from playwright.async_api import async_playwright, Browser, Page, Playwright

# ---------------------------------------------------------------------------
# Shared browser state (module-level singleton)
# ---------------------------------------------------------------------------

_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None


async def _get_page() -> Page:
    """Lazily initialise Playwright and return the shared page."""
    global _playwright, _browser, _page

    if _page is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await _browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        _page = await context.new_page()

    return _page


async def close_browser() -> None:
    """Gracefully shut down the shared browser."""
    global _playwright, _browser, _page
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _playwright = _browser = _page = None


# ---------------------------------------------------------------------------
# LangChain async tools
# ---------------------------------------------------------------------------


@tool
async def navigate(url: str) -> str:
    """Navigate the browser to the given URL. Returns title, HTTP status, and final URL as JSON."""
    try:
        page = await _get_page()
        response = await page.goto(url, wait_until="networkidle", timeout=30_000)
        title = await page.title()
        status = response.status if response else "unknown"
        return json.dumps({"title": title, "status": status, "url": page.url})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def extract_pt_cards() -> str:
    """Extract all personal trainer cards visible on the current page.
    Returns a JSON array of trainer profiles."""
    try:
        page = await _get_page()

        await page.wait_for_selector("pad.contacts", timeout=10_000)

        # JS runs in the browser — \\w is valid JS regex, not Python
        trainers = await page.evaluate(
            r"""
            () => {
                const cards = document.querySelectorAll("pad.contacts");

                return Array.from(cards).map(card => {
                    const onclickAttr = card.querySelector("[onclick]")
                        ?.getAttribute("onclick") ?? "";
                    const idMatch = onclickAttr.match(
                        /['"]([\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12})['"]/
                    );
                    const trainer_id = idMatch ? idMatch[1] : null;

                    const location = card.querySelector(
                        "icon.profile-icon-location + p3, icon.profile-icon-location ~ p3"
                    )?.innerText?.trim() ?? null;

                    const qualifications = card.querySelector(
                        "icon.profile-icon-qualifications + p3, icon.profile-icon-qualifications ~ p3"
                    )?.innerText?.trim() ?? null;

                    const phoneHref = card.querySelector(
                        "a[href^='tel:']"
                    )?.getAttribute("href") ?? null;
                    const phone = phoneHref ? phoneHref.replace("tel:", "") : null;

                    const emailHref = card.querySelector(
                        "a[href^='mailto:']"
                    )?.getAttribute("href") ?? null;
                    const email = emailHref ? emailHref.replace("mailto:", "") : null;

                    const whatsapp = card.querySelector(
                        "a[href*='wa.me']"
                    )?.getAttribute("href") ?? null;

                    return { trainer_id, location, qualifications, phone, email, whatsapp };
                });
            }
            """
        )

        return json.dumps(trainers, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "hint": "No PT cards found on this page. You may need to navigate through the flow first."})


@tool
async def paginate() -> str:
    """Click the next-page button and wait for new results.
    Returns 'next_page' if more pages exist, 'done' if on the last page."""
    try:
        page = await _get_page()

        next_selectors = [
            "button[aria-label='Next page']",
            "a[aria-label='Next page']",
            ".pagination__next:not([disabled])",
            "[data-testid='pagination-next']:not([disabled])",
            "li.next:not(.disabled) a",
            "button.next-page:not(:disabled)",
        ]

        for selector in next_selectors:
            next_btn = await page.query_selector(selector)
            if next_btn:
                is_disabled = await next_btn.get_attribute("disabled")
                aria_disabled = await next_btn.get_attribute("aria-disabled")

                if is_disabled is not None or aria_disabled == "true":
                    return "done"

                await next_btn.click()
                await page.wait_for_load_state("networkidle", timeout=15_000)
                return "next_page"

        return "done"
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def click(selector: str) -> str:
    """Click an element on the page by CSS selector. Returns 'clicked' on success or an error."""
    try:
        page = await _get_page()
        await page.click(selector, timeout=10_000)
        await page.wait_for_load_state("networkidle", timeout=15_000)
        return json.dumps({"status": "clicked", "selector": selector})
    except Exception as e:
        return json.dumps({"error": str(e), "selector": selector})


@tool
async def fill(selector: str, value: str) -> str:
    """Fill a text input on the page. Provide a CSS selector and the value to type."""
    try:
        page = await _get_page()
        await page.fill(selector, value, timeout=10_000)
        return json.dumps({"status": "filled", "selector": selector, "value": value})
    except Exception as e:
        return json.dumps({"error": str(e), "selector": selector})


@tool
async def get_page_content() -> str:
    """Get the visible text content and interactive elements on the current page.
    Useful for understanding page structure before clicking or filling."""
    try:
        page = await _get_page()
        content = await page.evaluate(
            r"""
            () => {
                const buttons = Array.from(document.querySelectorAll('button, [role="button"], a.btn'))
                    .map(el => ({tag: el.tagName, id: el.id, text: el.innerText?.trim(), class: el.className}))
                    .filter(el => el.text);
                const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
                    .map(el => ({tag: el.tagName, id: el.id, name: el.name, type: el.type, placeholder: el.placeholder}));
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .map(el => ({text: el.innerText?.trim(), href: el.href}))
                    .filter(el => el.text);
                const headings = Array.from(document.querySelectorAll('h1,h2,h3'))
                    .map(el => el.innerText?.trim());
                return {headings, buttons: buttons.slice(0, 30), inputs: inputs.slice(0, 20), links: links.slice(0, 30)};
            }
            """
        )
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def evaluate_js(script: str) -> str:
    """Run arbitrary JavaScript in the browser and return the result as JSON.
    Use this to call SPA functions like load_screen('experts.search') or to query the DOM."""
    try:
        page = await _get_page()
        result = await page.evaluate(script)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def screenshot(label: str = "") -> str:
    """Take a full-page screenshot for debugging. Returns the saved file path."""
    try:
        page = await _get_page()

        os.makedirs("screenshots", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = f"_{label}" if label else ""
        path = f"screenshots/va{slug}_{ts}.png"

        await page.screenshot(path=path, full_page=True)
        return path
    except Exception as e:
        return json.dumps({"error": str(e)})
