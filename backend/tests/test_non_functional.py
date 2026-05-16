from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_cors_rejects_unknown_origin_and_errors_include_request_id() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            cors_response = await client.options(
                "/health",
                headers={
                    "Origin": "https://unknown.example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert cors_response.status_code == 400
            assert "access-control-allow-origin" not in cors_response.headers

            error_response = await client.get(
                "/admin/api/v1/auth/me",
                headers={"X-Request-Id": "req-non-functional"},
            )
            assert error_response.status_code == 401, error_response.text
            assert error_response.json()["error"]["request_id"] == "req-non-functional"
