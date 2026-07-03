"""根路径健康路由(openspec change add-root-health-route)"""

import httpx
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_root_returns_ok():
    """探活请求根路径返回 200 {"status":"ok"},不再 404"""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
