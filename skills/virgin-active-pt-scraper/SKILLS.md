---
name: virgin-active-pt-scraper
description: >
  Scrape personal trainer profiles from experts.virginactive.co.za, extract structured contact and
  qualification data, and store results in a database or JSON file. Use this skill whenever the
  user wants to collect PT profiles, phone numbers, emails, Instagram handles, or other contact
  data from Virgin Active. Also use when the user mentions "scraping Virgin Active", "getting PT
  data", "building the trainer pipeline", or asks to run or extend the scraper.
---

# Virgin Active PT Scraper

Scrapes PT profiles from `https://experts.virginactive.co.za/web` using Playwright.

---

## Navigation flow

```
1. GET https://experts.virginactive.co.za/web
2. Click button#find-expert  ("Help me find an expert")
3. Select "Personal Trainer" → click Next
4. Filter by province + club → click Next
5. Paginate through PT listing cards
6. For each card: click → scrape detail page → go back
```

---

## Reference files — read these as needed

| File | Read when… |
|---|---|
| `references/selectors.md` | Implementing any DOM extraction (listing or detail page) |
| `references/schema.md` | Defining the data model, normalising fields, handling edge cases |
| `references/anti-detection.md` | Writing the Playwright setup, delays, or pagination loop |

---

## Quick-start checklist

1. `pip install playwright && playwright install chromium`
2. Read `references/anti-detection.md` → set up browser context + delay helper
3. Read `references/selectors.md` → wire up extraction for listing + detail pages
4. Read `references/schema.md` → map raw values into the `PTProfile` dataclass
5. Test on a single gym before a full run
6. Output to JSONL (`pts.jsonl`) or insert into `personal_trainers` table