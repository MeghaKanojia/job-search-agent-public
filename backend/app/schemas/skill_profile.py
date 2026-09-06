import datetime as dt

from pydantic import BaseModel, ConfigDict


class SkillProfileItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_name: str
    category: str | None
    proficiency_level: str | None
    years_experience: float | None
    evidence_bullet: str | None
    is_active: bool
    sort_order: int
    updated_at: dt.datetime


class SkillProfileItemCreate(BaseModel):
    skill_name: str
    category: str | None = None
    proficiency_level: str | None = None
    years_experience: float | None = None
    evidence_bullet: str | None = None
    sort_order: int = 0


class SkillProfileItemUpdate(BaseModel):
    skill_name: str | None = None
    category: str | None = None
    proficiency_level: str | None = None
    years_experience: float | None = None
    evidence_bullet: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
