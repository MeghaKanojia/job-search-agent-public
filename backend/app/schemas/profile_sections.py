"""Pydantic schemas for the Education / Work Experience / Projects /
Certifications sections of the profile. Grouped in one file since all four
follow the same Out/Create/Update shape as skill_profile_items.
"""

import datetime as dt

from pydantic import BaseModel, ConfigDict


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    institution: str
    degree: str
    field_of_study: str | None
    location: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    grade: str | None
    description: str | None
    is_active: bool
    sort_order: int
    updated_at: dt.datetime


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    location: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    grade: str | None = None
    description: str | None = None
    sort_order: int = 0


class EducationUpdate(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    location: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    grade: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class WorkExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    role_title: str
    location: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    is_current: bool
    description: str | None
    is_active: bool
    sort_order: int
    updated_at: dt.datetime


class WorkExperienceCreate(BaseModel):
    company: str
    role_title: str
    location: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_current: bool = False
    description: str | None = None
    sort_order: int = 0


class WorkExperienceUpdate(BaseModel):
    company: str | None = None
    role_title: str | None = None
    location: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_current: bool | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None
    tech_stack: str | None
    project_url: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    is_active: bool
    sort_order: int
    updated_at: dt.datetime


class ProjectCreate(BaseModel):
    title: str
    description: str | None = None
    tech_stack: str | None = None
    project_url: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    sort_order: int = 0


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    tech_stack: str | None = None
    project_url: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    issuing_organization: str | None
    issue_date: dt.date | None
    credential_url: str | None
    description: str | None
    is_active: bool
    sort_order: int
    updated_at: dt.datetime


class CertificationCreate(BaseModel):
    name: str
    issuing_organization: str | None = None
    issue_date: dt.date | None = None
    credential_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class CertificationUpdate(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_date: dt.date | None = None
    credential_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
