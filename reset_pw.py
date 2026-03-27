import asyncio
from app.core.database import get_engine
from app.auth.service import AuthService
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def reset():
    engine = get_engine()
    async with AsyncSession(engine) as db:
        pw = get_settings().auth.demo_user_password
        h = AuthService.hash_password(pw)
        await db.execute(
            text("UPDATE users SET hashed_password=:pw WHERE email=:e"),
            {"pw": h, "e": "admin@email-hub.dev"},
        )
        await db.commit()
        print("Password reset to:", pw)

asyncio.run(reset())
