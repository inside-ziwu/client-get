from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEV_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:4173",
    "http://localhost:4174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:4174",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="ClientGet Backend", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")

    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="change-me-now", alias="ADMIN_PASSWORD")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/clientget",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/clientget",
        alias="SYNC_DATABASE_URL",
    )
    test_database_url: str | None = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/clientget_test",
        alias="TEST_DATABASE_URL",
    )
    test_sync_database_url: str | None = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/clientget_test",
        alias="TEST_SYNC_DATABASE_URL",
    )

    allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:3001,https://client-get-admin.vercel.app,https://client-get-tenant.vercel.app",
        alias="ALLOWED_ORIGINS",
    )
    data_source_encryption_key: str = Field(
        default="0123456789abcdef0123456789abcdef",
        alias="DATA_SOURCE_ENCRYPTION_KEY",
    )
    internal_service_secret: str = Field(default="change-me-internal", alias="INTERNAL_SERVICE_SECRET")
    engagelab_webhook_secret: str = Field(
        default="change-me-webhook",
        alias="ENGAGELAB_WEBHOOK_SECRET",
    )
    engagelab_base_url: str | None = Field(default=None, alias="ENGAGELAB_BASE_URL")
    engagelab_send_path: str = Field(default="/v1/mail/send", alias="ENGAGELAB_SEND_PATH")
    engagelab_api_key: str | None = Field(default=None, alias="ENGAGELAB_API_KEY")
    engagelab_auth_header: str = Field(default="Authorization", alias="ENGAGELAB_AUTH_HEADER")
    engagelab_auth_scheme: str = Field(default="Bearer", alias="ENGAGELAB_AUTH_SCHEME")
    engagelab_timeout_seconds: float = Field(default=10.0, alias="ENGAGELAB_TIMEOUT_SECONDS")
    # EngageLab HTTP Basic Auth 字段（优先于 engagelab_api_key）
    # 参考 aoqi-ai/sysdev-ft-marketing：认证方式为 Basic base64(api_user:credential)
    engagelab_api_user: str | None = Field(default=None, alias="ENGAGELAB_API_USER")
    engagelab_credential: str | None = Field(default=None, alias="ENGAGELAB_CREDENTIAL")
    # 注：from_email 不在全局配置；发件地址来自 send_plans.sender_email（各租户自己的暖域名）
    collection_scheduler_sleep_seconds: int = Field(default=30, alias="COLLECTION_SCHEDULER_SLEEP_SECONDS")
    collection_worker_sleep_seconds: int = Field(default=10, alias="COLLECTION_WORKER_SLEEP_SECONDS")
    collection_task_lease_seconds: int = Field(default=300, alias="COLLECTION_TASK_LEASE_SECONDS")
    collection_worker_limit: int = Field(default=20, alias="COLLECTION_WORKER_LIMIT")
    collection_heartbeat_interval_seconds: int = Field(
        default=30,
        alias="COLLECTION_HEARTBEAT_INTERVAL_SECONDS",
    )
    wmt_lineage_repair_enabled: bool = Field(default=True, alias="WMT_LINEAGE_REPAIR_ENABLED")
    wmt_lineage_repair_interval_seconds: int = Field(
        default=300,
        alias="WMT_LINEAGE_REPAIR_INTERVAL_SECONDS",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return bool(value)

    @property
    def allowed_origins(self) -> list[str]:
        origins = [item.strip() for item in self.allowed_origins_raw.split(",") if item.strip()]
        if self.app_env.lower() not in {"prod", "production"}:
            for origin in LOCAL_DEV_ORIGINS:
                if origin not in origins:
                    origins.append(origin)
        return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
