"""Deterministic Playwright scraper for Virgin Active PT profiles.

The site is a SPA at experts.virginactive.co.za/web using custom HTML elements
(<expert>, <opt>, <btn>, <pad>, <screen>). All navigation happens via JS
load_screen() calls — the URL never changes.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from scraper.browser import BrowserManager, human_delay
from scraper.selectors import (
    CLUB_ITEM,
    DETAIL_EXTRACTION_JS,
    EXPERT_CARD,
    FIND_EXPERT_BTN,
    LISTING_EXTRACTION_JS,
    NEXT_BTN,
    PT_OPTION,
    SHOW_ALL_OPTION,
)

BASE_URL = "https://experts.virginactive.co.za/web"

# Map user-friendly location names to the site's data-region values
LOCATION_TO_REGION = {
     "cape town": "westerncape",
     "western cape": "westerncape",
     "johannesburg": "gauteng",
     "pretoria": "gauteng",
     "gauteng": "gauteng",
     "durban": "kwazulu-natal",
     "kwazulu-natal": "kwazulu-natal",
    "eastern cape": "easterncape",
    "port elizabeth": "easterncape",
     "east london": "easterncape",
     "free state": "freestate",
     "bloemfontein": "freestate",
     "mpumalanga": "mpumalanga",
     "limpopo": "limpopo",
     "north west": "northwest",
     "northern cape": "northerncape",
    "namibia": "namibia",
     "botswana": "botswana",
}


def _to_e164_za(num: str) -> str:
    """Normalise a South African phone number to E.164."""
    num = num.strip().replace(" ", "").replace("-", "")
    if num.startswith("0"):
        return "+27" + num[1:]
    if num.startswith("27") and not num.startswith("+"):
        return "+" + num
    if not num.startswith("+"):
        return "+27" + num
    return num


def _normalise_profile(raw: dict, gym_slug: str, gym_name: str, location: str) -> dict:
    """Clean and normalise a raw profile dict for DB insertion."""
    quals_raw = raw.get("qualifications") or ""
    qualifications = [q.strip() for q in quals_raw.split(",") if q.strip()] if quals_raw else []

    phone = raw.get("phone")
    if phone:
        phone = _to_e164_za(phone)

    whatsapp = raw.get("whatsapp_number")
    if whatsapp:
        whatsapp = _to_e164_za(whatsapp)

    profile_url = raw.get("profile_url") or raw.get("trainer_id") or ""

    return {
        "name": raw.get("name") or "Unknown",
        "gym_name": gym_name,
        "gym_slug": gym_slug,
        "location": location,
        "suburb": raw.get("suburb"),
        "qualifications": qualifications,
        "phone": phone,
        "email": raw.get("email"),
        "website": raw.get("website"),
        "instagram_handle": raw.get("instagram_handle"),
        "facebook_url": raw.get("facebook_url"),
        "whatsapp_number": whatsapp,
        "profile_url": profile_url,
        "profile_image_url": raw.get("profile_image_url") or raw.get("image_url"),
        "scraped_at": datetime.now(timezone.utc),
    }


async def _start_wizard(page: Page):
    """Navigate to the site and click through to the role selection step."""
    await page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
    await human_delay()
    await page.click(FIND_EXPERT_BTN, timeout=10_000)
    await page.wait_for_load_state("networkidle", timeout=15_000)
    await human_delay()


async def _select_pt_and_club(page: Page, club_slug: str):
    """Select Personal Trainer, then the given club, using 'show all' for remaining steps."""
    # Step 1: Select "Personal Trainer"
    await page.evaluate('document.querySelector(\'opt[data-value="personal-trainer"]\').click()')
    await human_delay()

    # Click Next
    await page.evaluate('document.querySelector("btn.next").click()')
    await human_delay(1000, 2000)

    # Step 2: Select club
    club_selector = f'div[data-club="{club_slug}"]'
    try:
        await page.wait_for_selector(club_selector, timeout=5_000)
        await page.click(club_selector)
    except PlaywrightTimeout:
        print(f"    Club {club_slug} not found in club list, skipping")
        return False
    await human_delay()

    # Click Next
    await page.evaluate('document.querySelector("btn.next").click()')
    await human_delay(1000, 2000)

    # Steps 3-5: Select "Show all" / first option for goal, gender, budget
    for step_num in range(3):
        # Try "Show all" option first, fall back to last option
        selected = await page.evaluate("""
            () => {
                const showAll = document.querySelector('opt[data-value="%na%"]:not(.selected)');
                if (showAll) { showAll.click(); return true; }
                // Fall back to last visible option
                const opts = document.querySelectorAll('step:not([style*="left: -"]):not([style*="left: 1"]) opt:not(.hidden)');
                if (opts.length > 0) { opts[opts.length - 1].click(); return true; }
                return false;
            }
        """)
        await human_delay()
        await page.evaluate('document.querySelector("btn.next")?.click()')
        await human_delay(1000, 2000)

    return True


async def _discover_clubs(page: Page, region: str) -> list[dict]:
    """From the club selection step, extract all clubs for a given region."""
    clubs = await page.evaluate(f"""
        () => {{
            const divs = document.querySelectorAll('div[data-region="{region}"][data-club]');
            return Array.from(divs).map(d => ({{
                id: d.getAttribute("data-club"),
                name: d.innerText.trim(),
                region: d.getAttribute("data-region"),
            }}));
        }}
    """)
    return clubs or []


async def _scrape_expert_details(page: Page, trainer_id: str, retries: int = 2) -> dict | None:
    """Navigate to an expert's profile screen and extract full contact details."""
    for attempt in range(retries + 1):
        try:
            # Navigate to profile via load_screen
            await page.evaluate(
                f"load_screen('experts.profile','next','p={trainer_id}')"
            )

            # Wait for the profile screen to become active, then for contacts
            await page.wait_for_selector(
                f'screen.experts-profile.ukey.cur, screen.cur pad.contacts',
                timeout=20_000,
            )
            await human_delay(500, 1000)

            # The screen may load before the contacts pad is populated — poll briefly
            for _ in range(5):
                has_pad = await page.evaluate(
                    "!!document.querySelector('screen.cur pad.contacts a')"
                )
                if has_pad:
                    break
                await human_delay(500, 800)

            data = await page.evaluate(DETAIL_EXTRACTION_JS)
            if data:
                data["trainer_id"] = trainer_id
                data["profile_url"] = trainer_id

            # Go back to listing
            await page.evaluate("screen_prev()")
            await human_delay(800, 1500)

            return data

        except PlaywrightTimeout:
            if attempt < retries:
                print(f"    Retry {attempt + 1}/{retries} for {trainer_id}")
                try:
                    await page.evaluate("screen_prev()")
                    await human_delay(1000, 2000)
                except Exception:
                    pass
                continue

            print(f"    Timeout loading profile {trainer_id} (all retries exhausted)")
            try:
                await page.evaluate("screen_prev()")
                await human_delay()
            except Exception:
                pass
            return None

        except Exception as e:
            print(f"    Error on profile {trainer_id}: {e}")
            try:
                await page.evaluate("screen_prev()")
                await human_delay()
            except Exception:
                pass
            return None


async def scrape_gym(page: Page, bm: BrowserManager, gym_slug: str, gym_name: str) -> list[dict]:
    """Scrape all PT profiles from a single gym. Returns raw profile dicts."""
    profiles: list[dict] = []

    # Start fresh wizard flow for this gym
    await _start_wizard(page)

    if not await _select_pt_and_club(page, gym_slug):
        return profiles

    # Wait for expert cards to appear
    try:
        await page.wait_for_selector(EXPERT_CARD, timeout=10_000)
    except PlaywrightTimeout:
        print(f"    No experts found at {gym_name}")
        return profiles

    # Get list of expert IDs from the listing
    experts = await page.evaluate(LISTING_EXTRACTION_JS)
    if not experts:
        return profiles

    print(f"    {len(experts)} experts listed at {gym_name}")

    # Visit each expert's detail page to get full contact info
    for expert in experts:
        trainer_id = expert.get("trainer_id")
        if not trainer_id:
            continue

        await human_delay()
        detail = await _scrape_expert_details(page, trainer_id)

        if detail:
            # Merge listing data (image, rate) with detail data
            detail["image_url"] = detail.get("profile_image_url") or expert.get("image_url")
            profiles.append(detail)
        else:
            # Use listing data as fallback (name only, no contacts)
            profiles.append({
                "name": expert.get("name"),
                "trainer_id": trainer_id,
                "profile_url": trainer_id,
                "image_url": expert.get("image_url"),
            })

        await bm.maybe_restart()
        # If browser was restarted, we need a new page and re-navigate
        if page.is_closed():
            page = await bm.new_page()
            await _start_wizard(page)
            if not await _select_pt_and_club(page, gym_slug):
                break

    return profiles


async def scrape_location(location: str) -> list[dict]:
    """Scrape all PT profiles for a given location. Returns normalised profile dicts."""
    region = LOCATION_TO_REGION.get(location.lower())
    if not region:
        raise ValueError(
            f"Unknown location: {location}. "
            f"Known locations: {', '.join(LOCATION_TO_REGION.keys())}"
        )

    all_profiles: list[dict] = []
    seen: set[str] = set()

    async with BrowserManager() as bm:
        page = await bm.new_page()

        # Navigate to wizard and discover clubs for this region
        await _start_wizard(page)

        # Select PT to get to club selection step
        await page.evaluate('document.querySelector(\'opt[data-value="personal-trainer"]\').click()')
        await human_delay()
        await page.evaluate('document.querySelector("btn.next").click()')
        await human_delay(1000, 2000)

        clubs = await _discover_clubs(page, region)
        await page.close()

        if not clubs:
            raise RuntimeError(f"No clubs found for region: {region}")

        print(f"Found {len(clubs)} clubs for {location} (region: {region})")

        # Scrape each club
        for club in clubs:
            gym_slug = club["id"]
            gym_name = club.get("name", gym_slug)
            print(f"Scraping {gym_name} ({gym_slug})...")

            page = await bm.new_page()
            try:
                raw_profiles = await scrape_gym(page, bm, gym_slug, gym_name)
                print(f"    Extracted {len(raw_profiles)} profiles from {gym_name}")

                for raw in raw_profiles:
                    profile = _normalise_profile(raw, gym_slug, gym_name, location)
                    key = profile["profile_url"]
                    if key and key not in seen:
                        seen.add(key)
                        all_profiles.append(profile)
            except Exception as e:
                print(f"    Failed on {gym_name}: {e}")
            finally:
                if not page.is_closed():
                    await page.close()

            # Save progress after each gym
            _save_progress(all_profiles, location)

    print(f"Total: {len(all_profiles)} unique profiles for {location}")
    return all_profiles


# All regions on the site (SA + Namibia + Botswana)
ALL_REGIONS = list(dict.fromkeys(LOCATION_TO_REGION.values()))


async def scrape_all_regions() -> list[dict]:
    """Scrape every region on the site. Returns normalised profile dicts."""
    all_profiles: list[dict] = []
    seen: set[str] = set()

    async with BrowserManager() as bm:
        page = await bm.new_page()

        # Discover clubs for every region in one wizard session
        await _start_wizard(page)
        await page.evaluate(
            'document.querySelector(\'opt[data-value="personal-trainer"]\').click()'
        )
        await human_delay()
        await page.evaluate('document.querySelector("btn.next").click()')
        await human_delay(1000, 2000)

        region_clubs: dict[str, list[dict]] = {}
        for region in ALL_REGIONS:
            clubs = await _discover_clubs(page, region)
            if clubs:
                region_clubs[region] = clubs
                print(f"  {region}: {len(clubs)} clubs")

        await page.close()

        total_clubs = sum(len(c) for c in region_clubs.values())
        print(f"Found {total_clubs} clubs across {len(region_clubs)} regions")

        # Reverse map region -> location label for DB storage
        region_to_label = {v: k.title() for k, v in LOCATION_TO_REGION.items()
                          if k == v or k.replace(" ", "") == v}
        # Ensure every region has a label
        for region in ALL_REGIONS:
            if region not in region_to_label:
                region_to_label[region] = region.title()

        # Scrape every club in every region
        for region, clubs in region_clubs.items():
            location_label = region_to_label[region]
            print(f"\n--- Region: {location_label} ({region}) ---")

            for club in clubs:
                gym_slug = club["id"]
                gym_name = club.get("name", gym_slug)
                print(f"Scraping {gym_name} ({gym_slug})...")

                page = await bm.new_page()
                try:
                    raw_profiles = await scrape_gym(page, bm, gym_slug, gym_name)
                    print(f"    Extracted {len(raw_profiles)} profiles from {gym_name}")

                    for raw in raw_profiles:
                        profile = _normalise_profile(
                            raw, gym_slug, gym_name, location_label
                        )
                        key = profile["profile_url"]
                        if key and key not in seen:
                            seen.add(key)
                            all_profiles.append(profile)
                except Exception as e:
                    print(f"    Failed on {gym_name}: {e}")
                finally:
                    if not page.is_closed():
                        await page.close()

                _save_progress(all_profiles, "all_regions")

    print(f"\nTotal: {len(all_profiles)} unique profiles across all regions")
    return all_profiles


CSV_COLUMNS = [
    "name", "gym_name", "gym_slug", "location", "suburb",
    "qualifications", "phone", "email", "website",
    "instagram_handle", "facebook_url", "whatsapp_number",
    "profile_url", "profile_image_url", "scraped_at",
]


def _save_progress(profiles: list[dict], location: str):
    """Save scraped profiles to JSON and CSV files."""
    slug = location.replace(" ", "_")
    serializable = []
    for p in profiles:
        row = dict(p)
        if isinstance(row.get("scraped_at"), datetime):
            row["scraped_at"] = row["scraped_at"].isoformat()
        serializable.append(row)

    # JSON (crash recovery)
    Path(f"scraped_{slug}.json").write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2)
    )

    # CSV
    csv_path = Path(f"scraped_{slug}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in serializable:
            # Join qualifications list into a semicolon-separated string for CSV
            r = dict(row)
            if isinstance(r.get("qualifications"), list):
                r["qualifications"] = "; ".join(r["qualifications"])
            writer.writerow(r)
