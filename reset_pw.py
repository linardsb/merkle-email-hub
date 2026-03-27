import asyncio
from app.core.database import AsyncSessionLocal
from app.auth.service import AuthService
from app.core.config import get_settings
from sqlalchemy import text

async def reset():
    async with AsyncSessionLocal() as db:
        pw = get_settings().auth.demo_user_password
        h = AuthService.hash_password(pw)
        await db.execute(
            text("UPDATE users SET hashed_password=:pw WHERE email=:e"),
            {"pw": h, "e": "admin@email-hub.dev"},
        )
        await db.commit()
        print("Password reset to:", pw)

asyncio.run(reset())
