import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.application import Application, ApplicationStatus
from app.models.document import Document
from app.models.job_posting import JobPosting
from app.models.status_proposal import StatusHistory, StatusUpdateProposal
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services.llm import available_providers
from app.services.rag import retrieve_relevant_skills
from app.services.tailoring import draft_cover_letter

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(status: ApplicationStatus | None = None, db: Session = Depends(get_db)):
    stmt = select(Application).order_by(Application.last_status_change_at.desc())
    if status is not None:
        stmt = stmt.where(Application.status == status)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=ApplicationOut)
def stage_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    """Stages a job posting as a candidate application for manual review.

    Per the approved apply-flow: this pipeline never auto-submits. Approval to
    `approved_ready_to_submit` is a separate explicit action the user takes here,
    not something the pipeline does on its own.
    """
    job_posting = db.get(JobPosting, payload.job_posting_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    application = Application(
        job_posting_id=payload.job_posting_id,
        company=job_posting.company,
        role_title=job_posting.title,
        source_portal=job_posting.source,
        jd_link=job_posting.url,
        status=ApplicationStatus.STAGED_FOR_REVIEW,
        notes=payload.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/llm_providers")
def list_llm_providers():
    """Which providers are actually configured right now -- backs the
    dashboard's provider dropdown for cover-letter drafting.
    """
    return {"providers": available_providers()}


@router.post("/{application_id}/draft_cover_letter")
def draft_cover_letter_for_application(
    application_id: int, provider: str | None = None, db: Session = Depends(get_db)
):
    """Drafts cover-letter body paragraphs via an LLM (Groq/Gemini,
    pick with ?provider=), grounded in RAG-retrieved relevant skills from your
    profile (see app/services/rag.py) -- not your entire profile dumped in,
    which keeps the prompt small regardless of how large your skill list
    grows. This is a first draft to review, not an auto-sent document -- the
    approved apply-flow still requires your manual review before anything
    goes out. Returns a static-template fallback (unfilled placeholders) if
    the LLM is unconfigured or the call fails, same as every other LLM
    integration in this project.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    job_posting = db.get(JobPosting, application.job_posting_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Linked job posting not found")

    jd_text = job_posting.description_raw or job_posting.title
    skills = retrieve_relevant_skills(db, jd_text, k=20)
    grounding_lines = [
        f"- {s.skill_name}" + (f": {s.evidence_bullet}" if s.evidence_bullet else "") for s in skills
    ]
    grounding_facts = "Candidate's most relevant skills/experience:\n" + "\n".join(grounding_lines)

    letter_body = draft_cover_letter(
        candidate_name="Alex Morgan",
        company=application.company or "the company",
        role_title=application.role_title or "the role",
        jd_text=jd_text,
        grounding_facts=grounding_facts,
        provider=provider,
    )

    if letter_body is None:
        return {
            "llm_generated": False,
            "body": (
                "[LLM unavailable -- fill in manually]\n\n"
                f"I'm writing to apply for the {application.role_title or '[ROLE TITLE]'} position "
                f"at {application.company or '[COMPANY NAME]'}. [Continue with your own draft, "
                "or configure a provider (GROQ_API_KEY/GEMINI_API_KEY) to enable "
                "automatic drafting.]"
            ),
        }
    return {"llm_generated": True, "body": letter_body}


@router.patch("/{application_id}/status", response_model=ApplicationOut)
def update_status(application_id: int, payload: ApplicationStatusUpdate, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = application.status
    application.status = payload.status
    application.last_status_change_at = dt.datetime.utcnow()
    if payload.notes is not None:
        application.notes = payload.notes
    if payload.status == ApplicationStatus.APPLIED and application.applied_at is None:
        application.applied_at = dt.datetime.utcnow()

    db.add(
        StatusHistory(
            application_id=application.id,
            old_status=old_status.value,
            new_status=payload.status.value,
            changed_by="user",
        )
    )
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """Removes this application from the tracker, along with everything that
    references it (generated/uploaded documents, status history, Gmail-derived
    status proposals) -- there's no ON DELETE CASCADE on those foreign keys, so
    this deletes them explicitly first, in one transaction. Does not touch the
    underlying job_postings row (New Matches is a separate list); this only
    un-tracks the application.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    db.execute(delete(Document).where(Document.application_id == application_id))
    db.execute(delete(StatusHistory).where(StatusHistory.application_id == application_id))
    db.execute(delete(StatusUpdateProposal).where(StatusUpdateProposal.application_id == application_id))
    db.delete(application)
    db.commit()
    return {"deleted": True}
