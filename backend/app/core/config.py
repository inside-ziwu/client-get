from __future__ import annotations

import os
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
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
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="ClientGet Backend", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    instance_id: str = Field(default="default", alias="CLIENTGET_INSTANCE_ID")

    # refresh cookie 的 Domain 属性,按实例配置(Instance A: .xinanpcb.com,
    # Instance B: 自己的域名);未设置时生产环境回退 .xinanpcb.com,保持
    # Instance A 零配置兼容,非生产环境不设置 Domain。
    cookie_domain: str = Field(default="", alias="COOKIE_DOMAIN")

    jwt_secret: str = Field(
        validation_alias=AliasChoices("CLIENTGET_JWT_SECRET", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    admin_email: str = Field(alias="ADMIN_EMAIL")
    admin_password: str = Field(alias="ADMIN_PASSWORD")

    clientget_dev_database_url: str = Field(default="", alias="CLIENTGET_DEV_DATABASE_URL")

    database_url: str = Field(default="", alias="DATABASE_URL")
    sync_database_url: str = Field(default="", alias="SYNC_DATABASE_URL")
    test_database_url: str | None = Field(default=None, alias="TEST_DATABASE_URL")
    test_sync_database_url: str | None = Field(default=None, alias="TEST_SYNC_DATABASE_URL")

    @model_validator(mode="after")
    def _require_instance_id_in_production(self) -> Settings:
        # 存量数据的 instance_id 均为 'default'（见 20260625_0100 迁移），
        # 因此 Instance A 生产合法取值就是 'default'；只要求显式设置以防漏配。
        if self.app_env.lower() in {"prod", "production"} and not os.environ.get(
            "CLIENTGET_INSTANCE_ID"
        ):
            raise ValueError("生产环境必须显式设置 CLIENTGET_INSTANCE_ID 环境变量（Instance A 为 'default'）")
        return self

    @model_validator(mode="after")
    def _derive_db_urls(self) -> Settings:
        if self.database_url or not self.clientget_dev_database_url:
            return self
        clean = self.clientget_dev_database_url.split("://", 1)[-1]
        # psycopg 直接使用原始参数
        self.sync_database_url = f"postgresql+psycopg://{clean}"
        # asyncpg 不认识 sslmode/channel_binding，需转换为 ssl=require
        base = clean.split("?")[0]
        use_ssl = "sslmode=require" in self.clientget_dev_database_url
        self.database_url = f"postgresql+asyncpg://{base}{'?ssl=require' if use_ssl else ''}"
        return self

    allowed_origins_raw: str = Field(
        default="",
        alias="ALLOWED_ORIGINS",
    )
    data_source_encryption_key: str = Field(alias="DATA_SOURCE_ENCRYPTION_KEY")
    internal_service_secret: str = Field(alias="INTERNAL_SERVICE_SECRET")
    engagelab_webhook_secret: str = Field(alias="ENGAGELAB_WEBHOOK_SECRET")
    engagelab_base_url: str | None = Field(default=None, alias="ENGAGELAB_BASE_URL")
    engagelab_send_path: str = Field(default="/v1/mail/send", alias="ENGAGELAB_SEND_PATH")
    engagelab_timeout_seconds: float = Field(default=10.0, alias="ENGAGELAB_TIMEOUT_SECONDS")
    # EngageLab HTTP Basic Auth：Basic base64(api_user:credential)
    engagelab_api_user: str | None = Field(default=None, alias="ENGAGELAB_API_USER")
    engagelab_credential: str | None = Field(default=None, alias="ENGAGELAB_CREDENTIAL")
    # 注：from_email 不在全局配置；发件地址来自 send_plans.sender_email（各租户自己的暖域名）
    wmt_lineage_repair_enabled: bool = Field(default=True, alias="WMT_LINEAGE_REPAIR_ENABLED")
    wmt_lineage_repair_interval_seconds: int = Field(
        default=300,
        alias="WMT_LINEAGE_REPAIR_INTERVAL_SECONDS",
    )
    industry_news_fetch_enabled: bool = Field(
        default=False,
        alias="INDUSTRY_NEWS_FETCH_ENABLED",
    )
    industry_news_fetch_hour_beijing: int = Field(
        default=8,
        ge=0,
        le=23,
        alias="INDUSTRY_NEWS_FETCH_HOUR_BEIJING",
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
