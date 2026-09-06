import datetime as dt

from pydantic import BaseModel, ConfigDict


class KeywordFilterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline: str
    keyword: str
    category: str | None
    is_active: bool
    created_at: dt.datetime


class KeywordFilterCreate(BaseModel):
    pipeline: str = "professional"
    keyword: str
    category: str | None = None  # "role" | "skill"
    is_active: bool = True


class KeywordFilterUpdate(BaseModel):
    keyword: str | None = None
    category: str | None = None
    is_active: bool | None = None


class PipelineSourceOut(BaseModel):
    key: str
    label: str
    enabled: bool


class SourceToggleUpdate(BaseModel):
    enabled: bool


class LLMStatusOut(BaseModel):
    configured_providers: list[str]
