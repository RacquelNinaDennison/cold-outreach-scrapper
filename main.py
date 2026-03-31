import asyncio

from db import AsyncSessionLocal
from db.crud import upsert_profiles
from db.init_db import create_all
from scraper import scrape_all_regions
from agents.nodes.outreach import generate_outreach


async def main():
    #await create_all()

    # Step 1: Scrape all regions (SA + Namibia + Botswana)
    profiles = await scrape_all_regions()
    print(f"Scraped {len(profiles)} profiles")

    # Step 2: Store
    #async with AsyncSessionLocal() as session:
    #    count = await upsert_profiles(session, profiles)
   # print(f"Stored {count} profiles")

    # # Step 3: Generate outreach for every location
    # locations = sorted({p["location"] for p in profiles})
    # total_emails = 0
    # for location in locations:
    #     emails = await generate_outreach(location)
    #     total_emails += len(emails)
    # print(f"Generated {total_emails} outreach emails across {len(locations)} locations")


if __name__ == "__main__":
    asyncio.run(main())
