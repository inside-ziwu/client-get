from typing import Any

import httpx


class OpenRouterError(Exception):
    def __init__(self, *, status_code: int, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}


class OpenRouterClient:
    base_url = "https://openrouter.ai"

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    async def get_credits(self, *, api_key: str) -> dict[str, Any]:
        return await self._get("/api/v1/credits", api_key=api_key)

    async def get_current_key(self, *, api_key: str) -> dict[str, Any]:
        return await self._get("/api/v1/key", api_key=api_key)

    async def _get(self, path: str, *, api_key: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.get(path, headers={"Authorization": f"Bearer {api_key}"})

        payload = self._safe_json(response)
        if response.status_code >= 400:
            message = None
            if isinstance(payload.get("error"), dict):
                message = payload["error"].get("message")
            if not message:
                message = payload.get("message")
            if not message:
                message = response.text or "OpenRouter 请求失败"
            raise OpenRouterError(status_code=response.status_code, message=str(message), payload=payload)

        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def _safe_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            return {"raw_text": response.text}
        if isinstance(data, dict):
            return data
        return {"data": data}
