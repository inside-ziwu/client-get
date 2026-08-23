"""行业动态请求模型。"""

from pydantic import BaseModel, Field


class IndustryNewsSourceToggle(BaseModel):
    """管理端启停动态源。"""

    is_active: bool = Field(..., description="是否启用")
