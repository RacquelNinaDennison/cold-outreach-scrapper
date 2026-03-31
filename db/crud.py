from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import OutreachEmail, PersonalTrainer


async def upsert_profiles(
    session: AsyncSession, profiles: list[dict]
) -> int:
    """Insert profiles, updating on conflict (gym_slug, profile_url). Returns count."""
    if not profiles:
        return 0

    stmt = pg_insert(PersonalTrainer).values(profiles)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_gym_profile",
        set_={
            "name": stmt.excluded.name,
            "gym_name": stmt.excluded.gym_name,
            "location": stmt.excluded.location,
            "suburb": stmt.excluded.suburb,
            "qualifications": stmt.excluded.qualifications,
            "phone": stmt.excluded.phone,
            "email": stmt.excluded.email,
            "website": stmt.excluded.website,
            "instagram_handle": stmt.excluded.instagram_handle,
            "facebook_url": stmt.excluded.facebook_url,
            "whatsapp_number": stmt.excluded.whatsapp_number,
            "profile_image_url": stmt.excluded.profile_image_url,
            "scraped_at": stmt.excluded.scraped_at,
        },
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount


async def get_profiles_without_outreach(
    session: AsyncSession, location: str
) -> list[PersonalTrainer]:
    """Return profiles in the given location that have no outreach email yet."""
    stmt = (
        select(PersonalTrainer)
        .outerjoin(OutreachEmail)
        .where(PersonalTrainer.location == location)
        .where(OutreachEmail.id.is_(None))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
