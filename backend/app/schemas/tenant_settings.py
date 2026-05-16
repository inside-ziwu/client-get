from pydantic import BaseModel, Field


class KeywordCreateRequest(BaseModel):
    keyword: str = Field(min_length=1)


class KeywordUpdateRequest(BaseModel):
    keyword: str | None = None
    status: str | None = None


class ScoringTemplateUpdateRequest(BaseModel):
    name: str | None = None
    dimensions: list[dict] | None = None
    grade_thresholds: dict | None = None


class ContactRulesUpdateRequest(BaseModel):
    name: str | None = None
    rules: dict
