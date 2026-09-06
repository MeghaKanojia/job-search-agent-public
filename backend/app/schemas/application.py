import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_posting_id: int
    company: str | None
    role_title: str | None
    source_portal: str | None
    status: ApplicationStatus
    applied_at: dt.datetime | None
    last_status_change_at: dt.datetime
    notes: str | None


class ApplicationCreate(BaseModel):
    job_posting_id: int
    notes: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: str | None = None
