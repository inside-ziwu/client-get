from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import APIModel


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=50, pattern=r"^[a-z0-9-]+$")
    industry: str = Field(min_length=2, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=50)
    admin_email: EmailStr
    admin_name: str = Field(min_length=1, max_length=100)
    admin_password: str = Field(min_length=8)
    # D-031：创建租户时同步配置发件域名和起始预热档位
    sender_domain: str | None = Field(default=None, max_length=255, description="发件域名，如 mail.example.com")
    warmup_level: int | None = Field(default=1, ge=1, description="起始预热档位（以当前实例激活预热规则的档位为准，默认 1）")


class TenantListItem(APIModel):
    id: str
    name: str
    slug: str
    industry: str
    status: str
    needs_onboarding: bool
    created_at: str | None = None
    updated_at: str | None = None


class TenantDetail(TenantListItem):
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
