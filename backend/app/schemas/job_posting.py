import datetime as dt

from pydantic import BaseModel, ConfigDict


class JobPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    title: str
    company: str | None
    location: str | None
    url: str
    salary_text: str | None
    posted_at: dt.datetime | None
    ingested_at: dt.datetime
    keyword_match_score: float | None
    matched_keywords: list | None
    relevance_reasoning: str | None
