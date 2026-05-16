from pydantic import BaseModel, Field


class OpenRouterConfigRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=500)
