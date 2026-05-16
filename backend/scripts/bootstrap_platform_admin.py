import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.ids import new_uuid
from app.security.passwords import hash_password


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO platform_users (id, email, password_hash, name, status)
                VALUES (:id, :email, :password_hash, :name, 'active')
                ON CONFLICT (email) DO UPDATE
                SET password_hash = excluded.password_hash,
                    name = excluded.name,
                    status = 'active',
                    updated_at = now()
                """
            ),
            {
                "id": str(new_uuid()),
                "email": settings.admin_email,
                "password_hash": hash_password(settings.admin_password),
                "name": "Platform Admin",
            },
        )
    await engine.dispose()
    print(f"Bootstrapped platform admin: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(main())
