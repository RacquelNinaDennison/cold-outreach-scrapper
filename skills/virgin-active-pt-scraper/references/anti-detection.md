# Anti-Detection & Pagination

---

## Browser context setup

```python
from playwright.async_api import async_playwright

async def make_context(playwright):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-ZA",
    )
    return browser, context
```

---

## Human-like delay helper

```python
import asyncio, random

async def human_delay(min_ms: int = 800, max_ms: int = 2500):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
```

Call between every meaningful action: card clicks, page transitions, form interactions.

---

## Pagination loop

```python
async def paginate(page, scrape_fn):
    while True:
        await page.wait_for_load_state("networkidle")
        await page.wait_for_selector(".trainer-card", timeout=10_000)

        links = await page.query_selector_all('a[href*="/personal-trainers/"]')
        urls = [await l.get_attribute("href") for l in links]

        for url in urls:
            await human_delay()
            await scrape_fn(page, url)

        next_btn = await page.query_selector("button.pagination__next")
        is_disabled = await next_btn.get_attribute("disabled") if next_btn else None
        if not next_btn or is_disabled is not None:
            break

        await next_btn.click()
        await human_delay(1000, 2000)
```

---

## Session batching

Restart the browser context every **30 profiles** to rotate state and avoid fingerprinting:

```python
BATCH_SIZE = 30
count = 0

for url in all_urls:
    if count > 0 and count % BATCH_SIZE == 0:
        await context.close()
        await browser.close()
        browser, context = await make_context(playwright)
        await human_delay(3000, 6000)  # longer pause between batches

    await scrape_detail(context, url)
    count += 1
```

---

## Rules of thumb

- Always `wait_for_load_state("networkidle")` after navigation — never fixed `sleep()`
- Never open more than one tab at a time
- Run during off-peak hours (early morning SA time) for lower server load
- If you get a 429 or blank page, back off for 60+ seconds before retrying