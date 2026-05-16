from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import APIModel


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TenantLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class AuthTokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"


class AdminMeResponse(APIModel):
    id: str
    email: EmailStr
    name: str
    roles: list[str]


class TenantMeResponse(APIModel):
    id: str
    tenant_id: str
    slug: str
    email: EmailStr
    name: str
    roles: list[str]
    needs_onboarding: bool
    must_change_pwd: bool
