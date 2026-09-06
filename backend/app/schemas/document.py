import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    doc_type: DocumentType
    version_number: int
    generated_at: dt.datetime
    content_text: str | None
    # Populated only by the list endpoint (joined from applications), so the
    # Resume Library can show "Mastercard - Data Engineer" without a second
    # round trip per row. None on the generate_resume/generate_cover_letter response.
    company: str | None = None
    role_title: str | None = None


class GeneratedDocumentOut(DocumentOut):
    # Transient, not persisted -- built fresh by generate_resume/generate_cover_letter
    # from what actually happened during that one generation call (e.g. an LLM call
    # falling back to raw/static content), so the dashboard can tell you when a
    # document is less AI-tailored than usual instead of silently looking normal.
    warnings: list[str] = []


class GenerateDocumentRequest(BaseModel):
    provider: str | None = None
    # Freeform tweak request ("emphasize my SQL experience more", "make this
    # shorter") threaded into the LLM prompt for this one generation call --
    # see tailoring.py's user_instructions handling. Never overrides the
    # no-fabrication guardrail, only tone/emphasis/structure/length.
    instructions: str | None = None


class DocumentContentUpdate(BaseModel):
    # Direct manual edit of a cover letter's body text. Resumes have no single
    # editable text blob (they're built from structured profile sections), so
    # this only applies to doc_type == cover_letter -- see documents.py.
    content_text: str
