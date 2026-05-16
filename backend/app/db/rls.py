from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def set_current_tenant(conn: AsyncConnection, tenant_id: str) -> None:
    await conn.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )
