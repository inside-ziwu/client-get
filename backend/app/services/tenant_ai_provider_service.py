from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.integrations.openrouter import OpenRouterClient, OpenRouterError
from app.services.audit_service import AuditService


class TenantAiProviderService:
    cache_ttl_seconds = 60

    def __init__(self, *, client: OpenRouterClient | None = None) -> None:
        self.client = client or OpenRouterClient()
        self.audit = AuditService()

    async def get_config(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        refresh_if_stale: bool = True,
    ) -> dict:
        row = await self._load_row(conn, tenant_id)
        if row is None:
            return self._serialize_absent(tenant_id)
        if refresh_if_stale and self._is_stale(row):
            await self.refresh_balance(conn, tenant_id=tenant_id, force=True)
            row = await self._load_row(conn, tenant_id)
        assert row is not None
        return self._serialize_row(row)

    async def upsert_config(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        api_key: str,
        user_id: str | None = None,
        platform_user_id: str | None = None,
    ) -> dict:
        existing = await self._load_row(conn, tenant_id)
        encrypted = encrypt_secret(api_key.strip())
        now = datetime.now(timezone.utc)
        if existing is None:
            config_id = str(new_uuid())
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_ai_provider_configs
                      (id, tenant_id, provider, api_key_encrypted, encryption_key_version,
                       configured_by_user_id, configured_by_platform_user_id, last_rotated_at,
                       balance_status, balance_currency, created_at, updated_at)
                    VALUES
                      (:id, :tenant_id, 'openrouter', :api_key_encrypted, 1,
                       :configured_by_user_id, :configured_by_platform_user_id, :last_rotated_at,
                       'unknown', 'USD', now(), now())
                    """
                ),
                {
                    "id": config_id,
                    "tenant_id": tenant_id,
                    "api_key_encrypted": encrypted,
                    "configured_by_user_id": user_id,
                    "configured_by_platform_user_id": platform_user_id,
                    "last_rotated_at": now,
                },
            )
        else:
            await conn.execute(
                text(
                    """
                    UPDATE tenant_ai_provider_configs
                    SET api_key_encrypted = :api_key_encrypted,
                        encryption_key_version = 1,
                        configured_by_user_id = :configured_by_user_id,
                        configured_by_platform_user_id = :configured_by_platform_user_id,
                        last_rotated_at = :last_rotated_at,
                        balance_status = 'unknown',
                        balance_source = NULL,
                        balance_amount = NULL,
                        total_credits = NULL,
                        total_usage = NULL,
                        key_limit = NULL,
                        key_limit_remaining = NULL,
                        balance_checked_at = NULL,
                        last_error_code = NULL,
                        last_error_message = NULL,
                        updated_at = now()
                    WHERE tenant_id = :tenant_id AND provider = 'openrouter'
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "api_key_encrypted": encrypted,
                    "configured_by_user_id": user_id,
                    "configured_by_platform_user_id": platform_user_id,
                    "last_rotated_at": now,
                },
            )
        after = await self.refresh_balance(conn, tenant_id=tenant_id, force=True)
        await self.audit.write(
            conn,
            action="update" if existing else "create",
            entity_type="tenant_ai_provider_config",
            entity_id=after["id"],
            tenant_id=tenant_id,
            user_id=user_id,
            platform_user_id=platform_user_id,
            old_value=self._serialize_row(existing) if existing else None,
            new_value=after,
        )
        return after

    async def delete_config(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str | None = None,
        platform_user_id: str | None = None,
    ) -> None:
        existing = await self._load_row(conn, tenant_id)
        if existing is None:
            return
        await conn.execute(
            text("DELETE FROM tenant_ai_provider_configs WHERE tenant_id = :tenant_id AND provider = 'openrouter'"),
            {"tenant_id": tenant_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="tenant_ai_provider_config",
            entity_id=str(existing["id"]),
            tenant_id=tenant_id,
            user_id=user_id,
            platform_user_id=platform_user_id,
            old_value=self._serialize_row(existing),
        )

    async def refresh_balance(self, conn: AsyncConnection, *, tenant_id: str, force: bool = False) -> dict:
        row = await self._load_row(conn, tenant_id)
        if row is None:
            raise AppError(code="OPENROUTER_NOT_CONFIGURED", message="当前租户尚未配置 OpenRouter API key", status_code=409)
        if not force and not self._is_stale(row):
            return self._serialize_row(row)

        api_key = decrypt_secret(row["api_key_encrypted"])
        state = await self._fetch_balance_state(api_key=api_key)
        await conn.execute(
            text(
                """
                UPDATE tenant_ai_provider_configs
                SET balance_status = :balance_status,
                    balance_source = :balance_source,
                    balance_amount = :balance_amount,
                    balance_currency = :balance_currency,
                    total_credits = :total_credits,
                    total_usage = :total_usage,
                    key_limit = :key_limit,
                    key_limit_remaining = :key_limit_remaining,
                    balance_checked_at = now(),
                    last_error_code = :last_error_code,
                    last_error_message = :last_error_message,
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND provider = 'openrouter'
                """
            ),
            {
                "tenant_id": tenant_id,
                "balance_status": state["balance_status"],
                "balance_source": state["balance_source"],
                "balance_amount": state["balance_amount"],
                "balance_currency": state["balance_currency"],
                "total_credits": state["total_credits"],
                "total_usage": state["total_usage"],
                "key_limit": state["key_limit"],
                "key_limit_remaining": state["key_limit_remaining"],
                "last_error_code": state["last_error_code"],
                "last_error_message": state["last_error_message"],
            },
        )
        refreshed = await self._load_row(conn, tenant_id)
        assert refreshed is not None
        return self._serialize_row(refreshed)

    async def assert_feature_available(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
    ) -> dict:
        state = await self.get_config(conn, tenant_id=tenant_id, refresh_if_stale=True)
        if not state["is_configured"]:
            raise AppError(code="OPENROUTER_NOT_CONFIGURED", message="当前租户尚未配置 OpenRouter API key", status_code=409)
        balance = state["balance"]
        status = balance["status"]
        if status == "available":
            return state
        if status == "insufficient_balance":
            raise AppError(code="INSUFFICIENT_BALANCE", message="OpenRouter 余额不足", status_code=402)
        if status == "invalid_api_key":
            raise AppError(code="INVALID_OPENROUTER_API_KEY", message="OpenRouter API key 无效", status_code=422)
        if status == "unknown":
            raise AppError(code="OPENROUTER_BALANCE_UNKNOWN", message="当前无法判定 OpenRouter 剩余额度", status_code=409)
        raise AppError(code="OPENROUTER_PROVIDER_ERROR", message=balance["message"] or "OpenRouter 服务暂时不可用", status_code=503)

    async def _fetch_balance_state(self, *, api_key: str) -> dict:
        try:
            credits = await self.client.get_credits(api_key=api_key)
            total_credits = self._to_decimal(credits.get("total_credits"))
            total_usage = self._to_decimal(credits.get("total_usage"))
            amount = total_credits - total_usage
            return {
                "balance_status": "available" if amount > 0 else "insufficient_balance",
                "balance_source": "credits",
                "balance_amount": amount,
                "balance_currency": "USD",
                "total_credits": total_credits,
                "total_usage": total_usage,
                "key_limit": None,
                "key_limit_remaining": None,
                "last_error_code": None,
                "last_error_message": None,
            }
        except OpenRouterError:
            pass

        try:
            key_info = await self.client.get_current_key(api_key=api_key)
        except OpenRouterError as exc:
            if exc.status_code == 401:
                return {
                    "balance_status": "invalid_api_key",
                    "balance_source": None,
                    "balance_amount": None,
                    "balance_currency": "USD",
                    "total_credits": None,
                    "total_usage": None,
                    "key_limit": None,
                    "key_limit_remaining": None,
                    "last_error_code": "invalid_api_key",
                    "last_error_message": exc.message,
                }
            return {
                "balance_status": "provider_error",
                "balance_source": None,
                "balance_amount": None,
                "balance_currency": "USD",
                "total_credits": None,
                "total_usage": None,
                "key_limit": None,
                "key_limit_remaining": None,
                "last_error_code": "provider_error",
                "last_error_message": exc.message,
            }

        key_limit_remaining = key_info.get("limit_remaining")
        key_limit = self._to_decimal(key_info.get("limit"))
        if key_limit_remaining is None:
            return {
                "balance_status": "unknown",
                "balance_source": "key",
                "balance_amount": None,
                "balance_currency": "USD",
                "total_credits": None,
                "total_usage": None,
                "key_limit": key_limit,
                "key_limit_remaining": None,
                "last_error_code": "balance_unknown",
                "last_error_message": "当前 key 未设置额度上限，无法判定剩余额度",
            }
        remaining = self._to_decimal(key_limit_remaining)
        return {
            "balance_status": "available" if remaining > 0 else "insufficient_balance",
            "balance_source": "key",
            "balance_amount": remaining,
            "balance_currency": "USD",
            "total_credits": None,
            "total_usage": None,
            "key_limit": key_limit,
            "key_limit_remaining": remaining,
            "last_error_code": None,
            "last_error_message": None,
        }

    async def _load_row(self, conn: AsyncConnection, tenant_id: str):
        result = await conn.execute(
            text(
                """
                SELECT c.*,
                       u.name AS configured_user_name,
                       u.email AS configured_user_email,
                       p.name AS configured_platform_user_name,
                       p.email AS configured_platform_user_email
                FROM tenant_ai_provider_configs c
                LEFT JOIN users u ON u.id = c.configured_by_user_id
                LEFT JOIN platform_users p ON p.id = c.configured_by_platform_user_id
                WHERE c.tenant_id = :tenant_id AND c.provider = 'openrouter'
                """
            ),
            {"tenant_id": tenant_id},
        )
        return result.mappings().first()

    def _serialize_absent(self, tenant_id: str) -> dict:
        return {
            "id": None,
            "tenant_id": tenant_id,
            "provider": "openrouter",
            "is_configured": False,
            "secret_masked": None,
            "configured_by": None,
            "last_rotated_at": None,
            "updated_at": None,
            "balance": {
                "status": "not_configured",
                "source": None,
                "amount": None,
                "currency": "USD",
                "checked_at": None,
                "message": "当前租户尚未配置 OpenRouter API key",
                "total_credits": None,
                "total_usage": None,
                "key_limit": None,
                "key_limit_remaining": None,
            },
        }

    def _serialize_row(self, row) -> dict:
        if row is None:
            raise ValueError("row is required")
        configured_by = None
        if row["configured_by_platform_user_id"]:
            configured_by = {
                "kind": "platform_user",
                "id": str(row["configured_by_platform_user_id"]),
                "name": row["configured_platform_user_name"],
                "email": row["configured_platform_user_email"],
            }
        elif row["configured_by_user_id"]:
            configured_by = {
                "kind": "tenant_user",
                "id": str(row["configured_by_user_id"]),
                "name": row["configured_user_name"],
                "email": row["configured_user_email"],
            }
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "provider": row["provider"],
            "is_configured": True,
            "secret_masked": self._mask_secret(decrypt_secret(row["api_key_encrypted"])),
            "configured_by": configured_by,
            "last_rotated_at": row["last_rotated_at"].isoformat() if row["last_rotated_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "balance": {
                "status": row["balance_status"],
                "source": row["balance_source"],
                "amount": self._decimal_to_float(row["balance_amount"]),
                "currency": row["balance_currency"],
                "checked_at": row["balance_checked_at"].isoformat() if row["balance_checked_at"] else None,
                "message": self._status_message(row["balance_status"], row["last_error_message"]),
                "total_credits": self._decimal_to_float(row["total_credits"]),
                "total_usage": self._decimal_to_float(row["total_usage"]),
                "key_limit": self._decimal_to_float(row["key_limit"]),
                "key_limit_remaining": self._decimal_to_float(row["key_limit_remaining"]),
            },
        }

    def _mask_secret(self, value: str) -> str:
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}***{value[-4:]}"

    def _is_stale(self, row) -> bool:
        checked_at = row["balance_checked_at"]
        if checked_at is None:
            return True
        return checked_at <= datetime.now(timezone.utc) - timedelta(seconds=self.cache_ttl_seconds)

    def _status_message(self, status: str, fallback: str | None) -> str | None:
        if status == "available":
            return "OpenRouter 余额可用"
        if status == "insufficient_balance":
            return "OpenRouter 余额不足"
        if status == "unknown":
            return fallback or "当前无法判定 OpenRouter 剩余额度"
        if status == "invalid_api_key":
            return fallback or "OpenRouter API key 无效"
        if status == "provider_error":
            return fallback or "OpenRouter 服务暂时不可用"
        return fallback

    def _to_decimal(self, value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def _decimal_to_float(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None
