import asyncio
from app.core.database import AsyncSessionLocal
from app.auth.service import AuthService
from app.core.config import get_settings
from sqlalchemy import text


async def reset():
    async with AsyncSessionLocal() as db:
        pw = get_settings().auth.demo_user_password

        # Check current user
        r = await db.execute(
            text("SELECT id, email, hashed_password FROM users WHERE email=:e"),
            {"e": "admin@email-hub.dev"},
        )
        row = r.first()
        if not row:
            print("ERROR: No user found with email admin@email-hub.dev")
            return

        print(f"User found: id={row[0]}, email={row[1]}")
        print(f"Current hash: {row[2][:30]}...")

        # Verify current password works
        matches = AuthService.verify_password(pw, row[2])
        print(f"Password '{pw}' matches current hash: {matches}")

        if not matches:
            # Force reset
            h = AuthService.hash_password(pw)
            await db.execute(
                text("UPDATE users SET hashed_password=:pw WHERE email=:e"),
                {"pw": h, "e": "admin@email-hub.dev"},
            )
            await db.commit()
            # Verify again
            r2 = await db.execute(
                text("SELECT hashed_password FROM users WHERE email=:e"),
                {"e": "admin@email-hub.dev"},
            )
            new_hash = r2.scalar_one()
            matches2 = AuthService.verify_password(pw, new_hash)
            print(f"After reset - password matches: {matches2}")
        else:
            print("Password already correct in DB - issue is elsewhere")


asyncio.run(reset())
