from pydantic import BaseModel, ConfigDict, Field


class ClaimTasksRequest(BaseModel):
    service_instance: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=5, ge=1, le=100)
    lease_seconds: int = Field(default=300, ge=30, le=3600)


class HeartbeatRequest(BaseModel):
    lease_id: str
    lease_seconds: int = Field(default=300, ge=30, le=3600)


class NormalizedCompany(BaseModel):
    """Accepts both old-style (source_type required) and new-style (target_table set) companies.
    Extra fields (country_iso3, collection_type, raw_payload, …) are forwarded as-is to the service.
    """

    model_config = ConfigDict(extra="allow")

    # New-style routing: set target_table to bypass shared_companies path
    target_table: str | None = None
    # Old-style required; optional when target_table is provided
    source_type: str | None = None
    source_id: str
    name: str
    name_en: str | None = None
    country: str | None = None
    website: str | None = None
    industry: str | None = None
    raw_data: dict = Field(default_factory=dict)


class NormalizedContact(BaseModel):
    source_type: str
    source_contact_id: str | None = None
    company_source_type: str
    company_source_id: str
    name: str | None = None
    email: str | None = None
    title: str | None = None
    raw_data: dict = Field(default_factory=dict)


class NormalizedCompetitor(BaseModel):
    company_name: str
    domain: str | None = None
    reason: str | None = None
    source_type: str = "lixiaoyun"
    raw_data: dict = Field(default_factory=dict)


class SubmitResultRequest(BaseModel):
    lease_id: str
    companies: list[NormalizedCompany] = Field(default_factory=list)
    contacts: list[NormalizedContact] = Field(default_factory=list)
    competitors: list[NormalizedCompetitor] = Field(default_factory=list)


class MarkFailedRequest(BaseModel):
    lease_id: str
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str = Field(min_length=1)
    retryable: bool = True
