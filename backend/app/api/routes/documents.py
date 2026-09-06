import datetime as dt

from fastapi import APIRouter, Body, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.application import Application
from app.models.certification import Certification
from app.models.document import Document, DocumentType
from app.models.education import Education
from app.models.job_posting import JobPosting
from app.models.project import Project
from app.models.skill_profile import SkillProfileItem
from app.models.work_experience import WorkExperience
from app.schemas.document import DocumentContentUpdate, DocumentOut, GeneratedDocumentOut, GenerateDocumentRequest
from app.services.document_templates import (
    DEFAULT_COVER_LETTER_TEMPLATE,
    DEFAULT_RESUME_TEMPLATE,
    render_html_template,
)
from app.services.matching import extract_keywords
from app.services.rag import retrieve_relevant_skills, retrieve_relevant_skills_with_status
from app.services.tailoring import (
    SkillProfileEntry,
    draft_cover_letter,
    draft_project_bullet,
    render_pdf,
    select_relevant_projects,
    select_relevant_skills,
)

router = APIRouter(prefix="/api", tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # a real resume PDF is a few hundred KB at most

# DEMO REPO NOTE: this is a sanitized replica of a private personal project,
# published as a portfolio/demo piece. The name below is real (this is my own
# project); every contact detail, employer, and project fact is a fictional
# placeholder, not real information.
#
# Matches the name hardcoded in applications.py's draft_cover_letter route --
# there's no per-user account system in this single-user tool, so these are
# literal constants rather than settings fields.
CANDIDATE_NAME = "Megha Kanojia"
CANDIDATE_HEADLINE = "Graduate Data Scientist | Python, SQL & Analytics Engineering"
CANDIDATE_SUMMARY = (
    "2026 MSc Computing (Data Analytics) graduate from Riverdale University, First Class "
    "Honours, exceeding the 2:1 threshold with a strong foundation in mathematics, statistics, "
    "and computer science. Impressive Python and SQL skills demonstrated through hands-on "
    "projects spanning machine learning, data pipelines (ETL), and analytics engineering. "
    "Proactive problem-solver with practical software engineering experience translating "
    "complex data into insights for cross-functional teams. Eager to specialise in a data "
    "domain and grow within a fast-paced, product-driven environment."
)
CANDIDATE_CONTACT = {
    "name": CANDIDATE_NAME,
    "headline": CANDIDATE_HEADLINE,
    "location": "Dublin, Ireland",
    "phone": "+353 1 234 5678",
    "email": "demo.sample.profile@example.com",
    "linkedin": "https://www.linkedin.com/in/demo-sample-profile",
    "github": "https://github.com/demo-sample-profile",
}


def _group_skills_by_category(skills: list[SkillProfileEntry]) -> list[dict]:
    """Groups skills by category, preserving each category's first-appearance
    order in `skills` (which is already JD-relevance sorted) so the most
    relevant categories bubble toward the top of the Technical Skills section.
    """
    grouped: dict[str, list[str]] = {}
    for s in skills:
        category = s.category or "Other"
        grouped.setdefault(category, []).append(s.skill_name)
    return [{"category": category, "skills": names} for category, names in grouped.items()]


def _bullet_lines(text: str | None) -> list[str]:
    """Splits a stored description into individual bullet lines for the resume
    template -- profile entries store multi-point descriptions one per line.
    """
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _select_relevant_skill_names(
    db: Session, jd_text: str, skills: list[SkillProfileEntry]
) -> tuple[list[str] | None, bool]:
    """Hybrid, non-LLM relevance filter for resume skills: exact keyword overlap
    with the JD (same logic select_relevant_skills's reorder already uses) UNION
    pgvector semantic similarity over skill_profile_items' embeddings. Cheaper,
    faster, and deterministic compared to asking an LLM to judge relevance --
    unlike projects (select_relevant_projects), skills are numerous, short, and
    already embedded, which is exactly what a vector search is good at.

    Returns (names_or_None, degraded) -- degraded is True if the semantic half
    fell back to the full skill list (embedding failure or nothing backfilled
    yet), so the caller can warn that this run only had keyword matching to
    work with. names is None only if keyword matching ALSO found nothing.
    """
    jd_words = extract_keywords(jd_text)
    keyword_matched = {s.skill_name for s in skills if s.skill_name.lower() in jd_words}
    semantic_items, degraded = retrieve_relevant_skills_with_status(db, jd_text, k=20)
    semantic_matched = {s.skill_name for s in semantic_items}
    combined = keyword_matched | semantic_matched
    return (list(combined) if combined else None), degraded


def _apply_relevance_filter(items: list, keep_names: list[str] | None, name_of, min_keep: int) -> list:
    """Narrows `items` down to the ones selected as JD-relevant, whether that
    selection came from select_relevant_projects's LLM call or
    _select_relevant_skill_names's keyword+embedding hybrid. Falls back to the
    full unfiltered list if selection failed (keep_names is None) or selected
    nothing at all (min_keep guards against an overly aggressive/broken
    selection wiping out the whole section) -- topping up from the remaining
    items, which are already sorted most-relevant-first, rather than cutting
    below min_keep.
    """
    if not keep_names:
        return items
    kept = [item for item in items if name_of(item) in keep_names]
    if not kept:
        return items
    if len(kept) < min_keep:
        remaining = [item for item in items if item not in kept]
        kept += remaining[: min_keep - len(kept)]
    return kept


def _fmt_month_year(value: dt.date | None) -> str | None:
    return value.strftime("%b %Y") if value else None


def _date_range(start: dt.date | None, end: dt.date | None, current: bool = False) -> str:
    s = _fmt_month_year(start)
    e = "Present" if current else _fmt_month_year(end)
    if s and e:
        return f"{s} - {e}"
    return s or e or ""


def _load_generation_context(application_id: int, db: Session) -> tuple[Application, str, str, str]:
    """Shared setup for both generate_resume and generate_cover_letter: fetches
    the application and its linked job posting, and derives the JD text used to
    tailor either document.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    job_posting = db.get(JobPosting, application.job_posting_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Linked job posting not found")

    jd_text = job_posting.description_raw or job_posting.title
    company = application.company or "the company"
    role_title = application.role_title or "the role"
    return application, jd_text, company, role_title


@router.post("/applications/{application_id}/generate_resume", response_model=GeneratedDocumentOut)
def generate_resume(
    application_id: int,
    payload: GenerateDocumentRequest = Body(default_factory=GenerateDocumentRequest),
    db: Session = Depends(get_db),
):
    """Generates a tailored resume PDF for this application. Every section is
    grounded strictly in your real profile data (skill_profile_items, education,
    work_experience, projects, certifications) -- tailoring.py's no-fabrication
    rule -- so this never invents experience you don't have. Project bullets are
    additionally rewritten per JD into Google's XYZ format via
    draft_project_bullet(), falling back to the raw stored description if the
    LLM is unconfigured or the call fails. Each call adds a new version rather
    than overwriting, so earlier versions stay available in the Resume Library.

    `payload.instructions`, when given, is your own tweak request for this
    regeneration (e.g. "put SQL higher", "shorten the forecasting project bullet") --
    threaded into each project bullet's LLM prompt, see tailoring.py.
    """
    provider = payload.provider
    warnings: list[str] = []
    _application, jd_text, _company, _role_title = _load_generation_context(application_id, db)

    # The resume draws from the FULL active profile (just reordered by relevance),
    # not the RAG top-K used for the cover letter below -- a resume should stay
    # comprehensive, while the cover-letter prompt stays deliberately small.
    all_active_skills = (
        db.execute(
            select(SkillProfileItem)
            .where(SkillProfileItem.is_active.is_(True))
            .order_by(SkillProfileItem.sort_order, SkillProfileItem.skill_name)
        )
        .scalars()
        .all()
    )
    entries = [
        SkillProfileEntry(skill_name=s.skill_name, category=s.category, evidence_bullet=s.evidence_bullet)
        for s in all_active_skills
    ]
    ordered_skills = select_relevant_skills(jd_text, entries)

    education = db.execute(
        select(Education).where(Education.is_active.is_(True)).order_by(Education.sort_order)
    ).scalars().all()
    experience = db.execute(
        select(WorkExperience).where(WorkExperience.is_active.is_(True)).order_by(WorkExperience.sort_order)
    ).scalars().all()
    projects = db.execute(
        select(Project).where(Project.is_active.is_(True)).order_by(Project.sort_order)
    ).scalars().all()
    certifications = db.execute(
        select(Certification).where(Certification.is_active.is_(True)).order_by(Certification.sort_order)
    ).scalars().all()

    # Narrows skills down to what's actually relevant to this JD using a hybrid of
    # exact keyword matching and pgvector semantic similarity over skill_profile_items'
    # embeddings (see _select_relevant_skill_names) -- deterministic and free, no LLM
    # call needed for this half of the filtering.
    selected_skill_names, skills_degraded = _select_relevant_skill_names(db, jd_text, ordered_skills)
    if skills_degraded:
        warnings.append(
            "Semantic skill matching was unavailable this run (embeddings not backfilled or failed to "
            "load); fell back to plain keyword matching, which may miss relevant skills phrased "
            "differently than the job description."
        )
    if selected_skill_names is None:
        warnings.append("Couldn't compute skill relevance at all; showing all skills.")
    ordered_skills = _apply_relevance_filter(ordered_skills, selected_skill_names, lambda s: s.skill_name, min_keep=6)

    # Projects are few enough per candidate, and their descriptions rich enough, that
    # an LLM relevance judgment is worth the extra call here (unlike skills, above).
    # See select_relevant_projects's docstring for why this carries no fabrication risk.
    selected_project_titles = select_relevant_projects(jd_text, [p.title for p in projects], provider=provider)
    if selected_project_titles is None:
        warnings.append("Couldn't determine project relevance via AI this run (LLM unavailable); included all projects.")
    projects = _apply_relevance_filter(projects, selected_project_titles, lambda p: p.title, min_keep=1)

    # Rewrites each project's stored description into a JD-tailored bullet in Google's
    # XYZ format (see tailoring.py's draft_project_bullet) -- falls back to the raw
    # stored description, unchanged, if the LLM is unconfigured or the call fails.
    tailored_project_descriptions: dict[int, str | None] = {}
    fallback_project_titles: list[str] = []
    for p in projects:
        if not p.description:
            tailored_project_descriptions[p.id] = p.description
            continue
        facts = p.description + (f"\nTech stack: {p.tech_stack}" if p.tech_stack else "")
        tailored = draft_project_bullet(
            p.title, facts, jd_text, provider=provider, user_instructions=payload.instructions
        )
        if tailored is None:
            fallback_project_titles.append(p.title)
        tailored_project_descriptions[p.id] = tailored or p.description
    if fallback_project_titles:
        warnings.append(
            f"LLM unavailable, used your original stored description for: {', '.join(fallback_project_titles)}."
        )

    resume_html = render_html_template(
        DEFAULT_RESUME_TEMPLATE,
        candidate=CANDIDATE_CONTACT,
        summary=CANDIDATE_SUMMARY,
        skill_groups=_group_skills_by_category(ordered_skills),
        education=[
            {
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "institution": e.institution,
                "location": e.location,
                "grade": e.grade,
                "bullets": _bullet_lines(e.description),
                "date_range": _date_range(e.start_date, e.end_date),
            }
            for e in education
        ],
        experience=[
            {
                "role_title": x.role_title,
                "company": x.company,
                "location": x.location,
                "bullets": _bullet_lines(x.description),
                "date_range": _date_range(x.start_date, x.end_date, x.is_current),
            }
            for x in experience
        ],
        projects=[
            {
                "title": p.title,
                "project_url": p.project_url,
                "bullets": _bullet_lines(tailored_project_descriptions[p.id]),
            }
            for p in projects
        ],
        certifications=[
            {
                "name": c.name,
                "description": c.description,
            }
            for c in certifications
        ],
    )
    resume_pdf = render_pdf(resume_html)

    resume_doc = Document(
        application_id=application_id,
        doc_type=DocumentType.RESUME,
        file_bytes=resume_pdf,
        content_text=None,
        version_number=_next_version(db, application_id, DocumentType.RESUME),
    )
    db.add(resume_doc)
    db.commit()
    db.refresh(resume_doc)
    return GeneratedDocumentOut(**DocumentOut.model_validate(resume_doc).model_dump(), warnings=warnings)


@router.post("/applications/{application_id}/generate_cover_letter", response_model=GeneratedDocumentOut)
def generate_cover_letter(
    application_id: int,
    payload: GenerateDocumentRequest = Body(default_factory=GenerateDocumentRequest),
    db: Session = Depends(get_db),
):
    """Generates a tailored cover-letter PDF for this application, grounded in
    your RAG-retrieved top-K most relevant skills/experience (tailoring.py's
    no-fabrication rule applies here too). Each call adds a new version rather
    than overwriting, so earlier versions stay available in the Resume Library.

    `payload.instructions`, when given, is your own tweak request for this
    regeneration (e.g. "make it punchier", "mention my Databricks project
    more") -- threaded into the LLM prompt, see tailoring.py.
    """
    provider = payload.provider
    warnings: list[str] = []
    _application, jd_text, company, role_title = _load_generation_context(application_id, db)

    rag_skills = retrieve_relevant_skills(db, jd_text, k=20)
    grounding_lines = [
        f"- {s.skill_name}" + (f": {s.evidence_bullet}" if s.evidence_bullet else "") for s in rag_skills
    ]
    grounding_facts = "Candidate's most relevant skills/experience:\n" + "\n".join(grounding_lines)
    letter_body = draft_cover_letter(
        candidate_name=CANDIDATE_NAME,
        company=company,
        role_title=role_title,
        jd_text=jd_text,
        grounding_facts=grounding_facts,
        provider=provider,
        user_instructions=payload.instructions,
    )
    if letter_body is None:
        warnings.append("LLM unavailable this run; used a static placeholder letter -- edit it manually before using it.")
        letter_body = (
            f"I'm writing to apply for the {role_title} position at {company}. "
            "[LLM unavailable this run -- edit this draft manually before using it.]"
        )

    letter_html = render_html_template(
        DEFAULT_COVER_LETTER_TEMPLATE,
        candidate_name=CANDIDATE_NAME,
        company=company,
        date_str=dt.date.today().strftime("%d %B %Y"),
        body=letter_body,
    )
    letter_pdf = render_pdf(letter_html)

    letter_doc = Document(
        application_id=application_id,
        doc_type=DocumentType.COVER_LETTER,
        file_bytes=letter_pdf,
        content_text=letter_body,
        version_number=_next_version(db, application_id, DocumentType.COVER_LETTER),
    )
    db.add(letter_doc)
    db.commit()
    db.refresh(letter_doc)
    return GeneratedDocumentOut(**DocumentOut.model_validate(letter_doc).model_dump(), warnings=warnings)


@router.post("/applications/{application_id}/upload_resume", response_model=DocumentOut)
async def upload_resume(application_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Attaches a resume PDF you built some other way (Canva, Word, another
    tool) to this application, as a new version alongside anything generated
    here -- for when you'd rather hand-tailor a resume than use this app's
    generator. Shows up in the Applications tracker's "Resume used" column
    and the Resume Library exactly like a generated one.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files can be uploaded as a resume")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large -- resumes should be well under 10 MB")
    doc = Document(
        application_id=application_id,
        doc_type=DocumentType.RESUME,
        file_bytes=file_bytes,
        content_text=None,
        version_number=_next_version(db, application_id, DocumentType.RESUME),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _next_version(db: Session, application_id: int, doc_type: DocumentType) -> int:
    current_max = db.execute(
        select(func.max(Document.version_number)).where(
            Document.application_id == application_id, Document.doc_type == doc_type
        )
    ).scalar()
    return (current_max or 0) + 1


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(application_id: int | None = None, db: Session = Depends(get_db)):
    """Every generated document, newest first. Backs both the Resume Library
    (no filter -- everything, across every application) and the Review Queue
    (filtered to one application's own documents).
    """
    stmt = (
        select(Document, Application.company, Application.role_title)
        .join(Application, Document.application_id == Application.id)
        .order_by(Document.generated_at.desc())
    )
    if application_id is not None:
        stmt = stmt.where(Document.application_id == application_id)

    out = []
    for doc, company, role_title in db.execute(stmt).all():
        item = DocumentOut.model_validate(doc)
        item.company = company
        item.role_title = role_title
        out.append(item)
    return out


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, inline: bool = False, db: Session = Depends(get_db)):
    """`inline=true` (used by the Resume Library / Review Queue "Preview" link)
    asks the browser to render the PDF in its own viewer instead of saving it
    to disk -- same bytes either way, just a different Content-Disposition.
    """
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    filename = f"{doc.doc_type.value}_v{doc.version_number}.pdf"
    disposition = "inline" if inline else "attachment"
    return Response(
        content=doc.file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def update_document_content(document_id: int, payload: DocumentContentUpdate, db: Session = Depends(get_db)):
    """Direct manual edit of a cover letter's body text -- re-renders the PDF
    from your edited text with no LLM call, updating this same row/version in
    place (unlike generate_cover_letter, which always adds a new version).
    Resumes have no single editable text blob (they're built from your
    structured profile sections), so this only supports doc_type == cover_letter;
    use generate_resume's `instructions` field to tweak a resume instead.
    """
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.doc_type != DocumentType.COVER_LETTER:
        raise HTTPException(
            status_code=400,
            detail="Only cover letters can be edited directly. Resumes are built from your "
            "structured profile data -- regenerate with instructions instead.",
        )
    application = db.get(Application, doc.application_id)
    letter_html = render_html_template(
        DEFAULT_COVER_LETTER_TEMPLATE,
        candidate_name=CANDIDATE_NAME,
        company=(application.company if application else None) or "the company",
        date_str=doc.generated_at.strftime("%d %B %Y"),
        body=payload.content_text,
    )
    doc.content_text = payload.content_text
    doc.file_bytes = render_pdf(letter_html)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"deleted": True}


@router.delete("/documents")
def delete_old_documents(older_than_days: int, db: Session = Depends(get_db)):
    """Manual bulk cleanup, on purpose not an automatic retention policy -- these
    PDFs live in Postgres (Neon), not on your disk, so this is about keeping the
    free-tier database tidy over time, triggered deliberately rather than
    silently deleting things you might still want.
    """
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=older_than_days)
    result = db.execute(delete(Document).where(Document.generated_at < cutoff))
    db.commit()
    return {"deleted_count": result.rowcount}
