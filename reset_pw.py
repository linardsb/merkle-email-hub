import asyncio
from app.core.database import AsyncSessionLocal
from app.auth.service import AuthService
from app.core.config import get_settings
from sqlalchemy import text


async def main():
    async with AsyncSessionLocal() as db:
        pw = get_settings().auth.demo_user_password

        # List all users
        r = await db.execute(text("SELECT id, email, role FROM users"))
        rows = r.fetchall()
        print(f"Total users: {len(rows)}")
        for row in rows:
            print(f"  id={row[0]} email={row[1]} role={row[2]}")

        if not rows:
            print("\nNo users found. Running seed...")
            from app.seed_demo import seed_all
            await seed_all(db)
            await db.commit()
            print("Seed complete.")
        else:
            # Reset password for first admin
            admin = next((r for r in rows if r[2] == "admin"), rows[0])
            h = AuthService.hash_password(pw)
            await db.execute(
                text("UPDATE users SET hashed_password=:pw WHERE email=:e"),
                {"pw": h, "e": admin[1]},
            )
            await db.commit()
            print(f"\nPassword for {admin[1]} reset to: {pw}")


asyncio.run(main())
