from pydantic import BaseModel


class ScoringTemplateUpdateRequest(BaseModel):
    name: str | None = None
    dimensions: list[dict] | None = None
    grade_thresholds: dict | None = None


class ContactRulesUpdateRequest(BaseModel):
    name: str | None = None
    rules: dict
