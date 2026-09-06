from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.settings import KeywordFilter, PipelineSetting
from app.schemas.settings import (
    KeywordFilterCreate,
    KeywordFilterOut,
    KeywordFilterUpdate,
    LLMStatusOut,
    PipelineSourceOut,
    SourceToggleUpdate,
)
from app.services.llm import available_providers

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Must match the connector `name` attributes in pipeline/connectors/* -- run_ingest.py
# reads the same source_setting_key() before running each one (see
# pipeline/common/pipeline_settings.py), so a source disabled here is skipped on the
# next scheduled run, not just hidden from the UI.
PIPELINE_SOURCES = [
    {"key": "jobspy", "label": "JobSpy (Indeed / LinkedIn search)"},
    {"key": "gmail_linkedin", "label": "Gmail LinkedIn job alerts"},
    {"key": "irish_boards", "label": "Irish job boards (jobs.ie / irishjobs.ie)"},
]


def _source_setting_key(source: str) -> str:
    return f"source_enabled:{source}"


# ---------------------------------------------------------------------------
# Keyword filters -- controls what the pipeline lands at all (see
# pipeline/keyword_filter.py's load_active_keywords/matches_filters)
# ---------------------------------------------------------------------------


@router.get("/keywords", response_model=list[KeywordFilterOut])
def list_keywords(pipeline: str = "professional", db: Session = Depends(get_db)):
    stmt = (
        select(KeywordFilter)
        .where(KeywordFilter.pipeline == pipeline)
        .order_by(KeywordFilter.category, KeywordFilter.keyword)
    )
    return db.execute(stmt).scalars().all()


@router.post("/keywords", response_model=KeywordFilterOut)
def create_keyword(payload: KeywordFilterCreate, db: Session = Depends(get_db)):
    keyword = KeywordFilter(**payload.model_dump())
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.patch("/keywords/{keyword_id}", response_model=KeywordFilterOut)
def update_keyword(keyword_id: int, payload: KeywordFilterUpdate, db: Session = Depends(get_db)):
    keyword = db.get(KeywordFilter, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(keyword, field, value)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    keyword = db.get(KeywordFilter, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(keyword)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Per-source pipeline toggles -- the "instant kill switch" promised in
# irish_boards_connector.py's docstring but never actually wired up before now.
# State lives in pipeline_settings, the same table run_ingest.py already reads
# for rate-limit state (see pipeline/common/rate_limiter.py), so no schema change.
# ---------------------------------------------------------------------------


@router.get("/pipeline_sources", response_model=list[PipelineSourceOut])
def list_pipeline_sources(db: Session = Depends(get_db)):
    keys = [_source_setting_key(s["key"]) for s in PIPELINE_SOURCES]
    rows = db.execute(select(PipelineSetting).where(PipelineSetting.key.in_(keys))).scalars().all()
    state = {row.key: row.value for row in rows}
    return [
        PipelineSourceOut(
            key=s["key"],
            label=s["label"],
            # Defaults to enabled -- a source with no row yet has never been
            # explicitly toggled off, so it should keep running as it always has.
            enabled=state.get(_source_setting_key(s["key"]), {}).get("enabled", True),
        )
        for s in PIPELINE_SOURCES
    ]


@router.patch("/pipeline_sources/{source_key}", response_model=PipelineSourceOut)
def set_pipeline_source(source_key: str, payload: SourceToggleUpdate, db: Session = Depends(get_db)):
    source = next((s for s in PIPELINE_SOURCES if s["key"] == source_key), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Unknown pipeline source")

    key = _source_setting_key(source_key)
    row = db.execute(select(PipelineSetting).where(PipelineSetting.key == key)).scalar_one_or_none()
    if row is None:
        db.add(PipelineSetting(key=key, value={"enabled": payload.enabled}))
    else:
        row.value = {"enabled": payload.enabled}
    db.commit()
    return PipelineSourceOut(key=source_key, label=source["label"], enabled=payload.enabled)


# ---------------------------------------------------------------------------
# LLM provider status -- read-only, backs a status indicator on the Settings
# page (whether GROQ_API_KEY / GEMINI_API_KEY are actually configured).
# ---------------------------------------------------------------------------


@router.get("/llm_status", response_model=LLMStatusOut)
def llm_status():
    return LLMStatusOut(configured_providers=available_providers())
