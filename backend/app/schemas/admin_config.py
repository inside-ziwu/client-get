"""管理端平台配置（admin/config）请求模型

app/api/admin/config.py 裸 dict 收参逐端点 Pydantic 化的落点。
字段口径以 service 层实际取值为准，默认值与表结构 DEFAULT 保持一致。
"""

from pydantic import BaseModel, Field

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
