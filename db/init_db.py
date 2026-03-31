from db.session import engine, Base
from db import models  # noqa: F401 — ensure models are registered


async def create_all():
    """Create all tables (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
