"""管理端平台配置（admin/config）请求模型

app/api/admin/config.py 裸 dict 收参逐端点 Pydantic 化的落点。
字段口径以 service 层实际取值为准，默认值与表结构 DEFAULT 保持一致。
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, RootModel

# 与 platform_scoring_templates.grade_thresholds 列默认值及
# service 层 create/update 的兜底值一致
_DEFAULT_GRADE_THRESHOLDS = {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0}


class ScoringTemplateCreate(BaseModel):
    """创建平台评分模板请求（POST /admin/api/v1/scoring-templates）"""

    industry: str = Field(min_length=1, max_length=100, description="行业")
    name: str = Field(min_length=1, max_length=200, description="模板名称")
    dimensions: list[dict] = Field(description="评分维度配置")
    description: str | None = Field(default=None, description="模板描述")
    is_active: bool = Field(default=True, description="是否激活")
    grade_thresholds: dict = Field(
        default_factory=lambda: dict(_DEFAULT_GRADE_THRESHOLDS),
        description="评分等级阈值，默认 S90/A80/B60/C40/D0",
    )


class EmailTemplateCreate(BaseModel):
    """创建平台邮件模板请求（POST /admin/api/v1/email-templates）"""

    industry: str = Field(..., min_length=1, max_length=100, description="行业")
    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    subject: str = Field(..., description="邮件主题")
    body_html: str = Field(..., description="HTML 正文")
    description: str | None = Field(None, description="模板描述")
    category: str = Field(default="default", min_length=1, max_length=50, description="模板分类")
    body_text: str | None = Field(None, description="纯文本正文")
    variables: list[dict] = Field(default_factory=list, description="模板变量")
    is_active: bool = Field(default=True, description="是否激活")


class IntelligenceSourceCreate(BaseModel):
    """创建平台情报源请求（POST /admin/api/v1/intelligence-sources）"""

    name: str = Field(..., min_length=1, max_length=200, description="情报源名称")
    source_type: Literal["rss", "website", "manual"] = Field(..., description="情报源类型")
    url: str | None = Field(None, description="情报源地址")
    fetch_config: dict = Field(
        default_factory=lambda: {"frequency_hours": 24},
        description="抓取配置",
    )
    industry_tags: list[str] = Field(default_factory=list, description="行业标签")
    is_active: bool = Field(default=True, description="是否激活")


class WarmupRuleLevelUpdate(BaseModel):
    """预热规则档位请求"""

    level: int = Field(..., ge=1, description="预热档位")
    daily_limit: int = Field(..., description="每日发送上限")
    min_stay_days: int = Field(default=1, description="最少停留天数")
    min_delivery_rate: float = Field(default=0.95, description="最低送达率")
    max_bounce_rate: float = Field(default=0.02, description="最高退信率")
    max_complaint_rate: float = Field(default=0.001, description="最高投诉率")


class WarmupRuleUpdate(BaseModel):
    """更新平台预热规则请求（PUT /admin/api/v1/warmup-rules）"""

    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    min_observation_emails: int = Field(default=20, description="最少观察邮件数")
    bounce_alert_rate: float = Field(default=0.05, description="退信告警率")
    config: dict = Field(default_factory=dict, description="规则配置")
    levels: list[WarmupRuleLevelUpdate] = Field(default_factory=list, description="预热档位")


class AIModelCreate(BaseModel):
    """创建 AI 模型配置请求（POST /admin/api/v1/ai-config/models）"""

    model_id: str = Field(..., min_length=1, max_length=150, description="模型代码")
    display_name: str = Field(..., min_length=1, max_length=100, description="展示名称")
    provider: str = Field(
        default="openrouter",
        min_length=1,
        max_length=50,
        description="模型供应商",
    )
    is_active: bool = Field(default=True, description="是否激活")
    config: dict = Field(default_factory=dict, description="模型配置")


class TenantUserCreate(BaseModel):
    """创建租户用户请求（POST /admin/api/v1/tenants/{tenant_id}/users）"""

    email: EmailStr = Field(..., max_length=255, description="用户邮箱")
    name: str = Field(..., min_length=1, max_length=100, description="用户姓名")
    password: str = Field(default="temporary-password", description="初始密码")
    status: Literal["active", "disabled"] = Field(default="active", description="用户状态")
    must_change_pwd: bool = Field(default=True, description="首次登录是否必须修改密码")
    roles: list[Literal["admin", "operator", "viewer"]] = Field(
        default_factory=lambda: ["viewer"],
        description="租户角色",
    )


class AIModelUpdate(BaseModel):
    """更新 AI 模型配置请求（PATCH /admin/api/v1/ai-config/models/{model_id}）"""

    provider: str | None = Field(None, min_length=1, max_length=50, description="模型供应商")
    model_id: str | None = Field(None, min_length=1, max_length=150, description="模型代码")
    display_name: str | None = Field(None, min_length=1, max_length=100, description="展示名称")
    is_active: bool | None = Field(None, description="是否激活")
    config: dict | None = Field(None, description="模型配置")


class AISceneDefaultUpdate(BaseModel):
    """单个 AI 场景默认模型配置"""

    scene: Literal[
        "scoring",
        "email_generation",
        "intelligence_summary",
        "data_analysis",
    ] = Field(..., description="AI 使用场景")
    model_id: str = Field(..., min_length=1, description="AI 模型行 ID")
    config: dict = Field(default_factory=dict, description="场景配置")


class AISceneDefaultsUpdate(RootModel[list[AISceneDefaultUpdate]]):
    """批量更新 AI 场景默认配置请求（PUT /admin/api/v1/ai-config/scene-defaults）"""


class AIPricingItemUpdate(BaseModel):
    """兼容旧版 AI 定价请求的单个模型价格"""

    model_id: str = Field(..., min_length=1, description="AI 模型行 ID")
    input_price: float = Field(..., description="输入价格")
    output_price: float = Field(..., description="输出价格")


class AIPricingUpdate(BaseModel):
    """更新 AI 定价配置请求（PUT /admin/api/v1/ai-config/pricing）"""

    items: list[AIPricingItemUpdate] = Field(
        default_factory=list,
        description="兼容旧版定价请求；当前价格列已移除",
    )


class ScoringTemplateUpdate(BaseModel):
    """更新平台评分模板请求（PUT /admin/api/v1/scoring-templates/{template_id}）"""

    industry: str | None = Field(None, min_length=1, max_length=100, description="行业")
    name: str | None = Field(None, min_length=1, max_length=200, description="模板名称")
    dimensions: list[dict] | dict | None = Field(None, description="评分维度配置")
    description: str | None = Field(None, description="模板描述")
    is_active: bool | None = Field(None, description="是否激活")
    grade_thresholds: dict | None = Field(None, description="评分等级阈值")


class EmailTemplateUpdate(BaseModel):
    """更新平台邮件模板请求（PUT /admin/api/v1/email-templates/{template_id}）"""

    industry: str | None = Field(None, min_length=1, max_length=100, description="行业")
    name: str | None = Field(None, min_length=1, max_length=200, description="模板名称")
    subject: str | None = Field(None, description="邮件主题")
    body_html: str | None = Field(None, description="HTML 正文")
    description: str | None = Field(None, description="模板描述")
    category: str | None = Field(None, min_length=1, max_length=50, description="模板分类")
    body_text: str | None = Field(None, description="纯文本正文")
    variables: list[dict] | None = Field(None, description="模板变量")
    is_active: bool | None = Field(None, description="是否激活")


class TenantUserUpdate(BaseModel):
    """局部更新租户用户请求"""

    email: EmailStr | None = Field(None, max_length=255, description="用户邮箱")
    name: str | None = Field(None, min_length=1, max_length=100, description="用户姓名")
    password: str | None = Field(None, description="新密码")
    status: Literal["active", "disabled"] | None = Field(None, description="用户状态")
    must_change_pwd: bool | None = Field(None, description="是否必须修改密码")
    roles: list[Literal["admin", "operator", "viewer"]] | None = Field(
        None,
        description="租户角色",
    )


class TenantUpdate(BaseModel):
    """局部更新租户请求（PATCH /admin/api/v1/tenants/{tenant_id}）"""

    name: str | None = Field(None, min_length=1, max_length=100, description="租户名称")
    industry: str | None = Field(None, min_length=1, max_length=100, description="行业")
    contact_name: str | None = Field(None, max_length=100, description="联系人姓名")
    contact_phone: str | None = Field(None, max_length=50, description="联系人电话")
    contact_email: EmailStr | None = Field(
        None,
        max_length=255,
        description="联系人邮箱",
    )


class IntelligenceSourceBatchImport(BaseModel):
    """批量导入平台情报源请求"""

    items: list[IntelligenceSourceCreate] = Field(..., description="待导入情报源")


class IntelligenceSourceUpdate(BaseModel):
    """局部更新平台情报源请求"""

    name: str | None = Field(None, min_length=1, max_length=200, description="情报源名称")
    source_type: Literal["rss", "website", "manual"] | None = Field(
        None,
        description="情报源类型",
    )
    url: str | None = Field(None, description="情报源地址")
    fetch_config: dict | None = Field(None, description="抓取配置")
    industry_tags: list[str] | None = Field(None, description="行业标签")
    is_active: bool | None = Field(None, description="是否激活")


class TenantDomainCreate(BaseModel):
    """添加租户发信域名请求"""

    domain: str = Field(..., min_length=1, max_length=255, description="发信域名")
    warmup_rule_id: str = Field(..., min_length=1, description="预热规则 ID")
    warmup_level: int = Field(..., ge=1, description="预热档位")
    spf_record: str | None = Field(None, description="SPF 记录")
    dkim_record: str | None = Field(None, description="DKIM 记录")
    dmarc_record: str | None = Field(None, description="DMARC 记录")
    verification_status: Literal[
        "pending",
        "verifying",
        "verified",
        "failed",
    ] = Field(default="pending", description="域名验证状态")
    sender_email: EmailStr | None = Field(
        None,
        max_length=255,
        description="发件邮箱",
    )
