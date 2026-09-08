from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import OwnerPreference


class PreferenceService:

    @staticmethod
    async def set_preference(db: AsyncSession, key: str, value: str) -> OwnerPreference:
        """Sets or updates a key-value store preference."""
        clean_key = key.strip().lower()
        stmt = select(OwnerPreference).where(OwnerPreference.key == clean_key)
        pref = (await db.execute(stmt)).scalar_one_or_none()

        if pref:
            pref.value = value.strip()
        else:
            pref = OwnerPreference(key=clean_key, value=value.strip())
            db.add(pref)

        await db.commit()
        await db.refresh(pref)
        return pref

    @staticmethod
    async def get_preference(db: AsyncSession, key: str) -> Optional[str]:
        """Retrieves a persistent setting value."""
        clean_key = key.strip().lower()
        stmt = select(OwnerPreference).where(OwnerPreference.key == clean_key)
        pref = (await db.execute(stmt)).scalar_one_or_none()
        return pref.value if pref else None

    @staticmethod
    async def get_all_preferences(db: AsyncSession) -> Dict[str, str]:
        """Loads all persistent settings into memory for LLM context injection."""
        stmt = select(OwnerPreference)
        prefs = (await db.execute(stmt)).scalars().all()
        return {p.key: p.value for p in prefs}