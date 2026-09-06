"""CV tailoring.

Hard rule, non-negotiable: this module may only ever surface skills/bullets that
already exist in `skill_profile_items` (your self-reported, truthful profile).
It reorders and emphasizes based on JD overlap — it never invents a skill you
don't actually have. `tests/test_tailoring.py` asserts this directly.

Resume rendering is template-based (Jinja2 + WeasyPrint), zero-cost and
zero-fabrication-risk by construction. Cover-letter drafting (draft_cover_letter,
below) uses a free-tier LLM (Groq/Gemini -- see app/services/llm/) for
natural phrasing, but is grounded strictly in facts you pass it -- the same
no-fabrication rule is enforced via a strict system prompt rather than by
construction, so treat any drafted letter as a first draft to skim before
sending, not an unreviewed final output.
"""

import json
import logging
from dataclasses import dataclass

from jinja2 import Environment, select_autoescape
from weasyprint import HTML

from app.services.llm import chat as llm_chat
from app.services.matching import extract_keywords

logger = logging.getLogger(__name__)


@dataclass
class SkillProfileEntry:
    skill_name: str
    category: str | None
    evidence_bullet: str | None


def select_relevant_skills(
    jd_text: str, profile: list[SkillProfileEntry]
) -> list[SkillProfileEntry]:
    """Filter + reorder the user's truthful skill profile by JD relevance.

    Never adds anything not already in `profile` — the return value is always
    a subset (reordered) of the input.
    """
    jd_words = extract_keywords(jd_text)
    matched = [s for s in profile if s.skill_name.lower() in jd_words]
    unmatched = [s for s in profile if s not in matched]
    return matched + unmatched


_RELEVANCE_SYSTEM_PROMPT = """You select which of a candidate's real projects are relevant enough
to include on a resume tailored to one specific job description.

Hard rules, non-negotiable:
- You may ONLY select from the exact PROJECT TITLES listed below. Never invent, rename, merge,
  or add anything not already in that list -- copy titles verbatim.
- This is a relevance filter, not a quality judgment: keep anything plausibly related to this
  JD's domain, tools, or role. When genuinely unsure, keep it rather than cut it -- never make
  the candidate look less capable than they are. Only cut what's clearly unrelated noise.
- Respond with ONLY a single JSON object, no prose, no markdown code fences, in exactly this
  shape: {"projects": ["<exact project title>", ...]}"""


def select_relevant_projects(
    jd_text: str,
    project_titles: list[str],
    provider: str | None = None,
) -> list[str] | None:
    """Asks the LLM which of the candidate's real project titles are relevant
    enough to include on a resume tailored to jd_text. This is a SELECTION
    task, not generation -- the model may only choose from the exact titles
    given, never invent new ones (documents.py additionally drops any
    hallucinated title that doesn't match the known set, belt and suspenders).

    Skills use a separate, non-LLM path (see documents.py's hybrid keyword +
    pgvector-embedding selection) -- projects are few enough per candidate,
    and their descriptions rich enough, that an LLM judgment call is worth the
    extra request here in a way it wasn't for skills.

    Returns None if the LLM is unconfigured, the call fails, or the response
    isn't valid JSON -- callers must fall back to keeping every project
    unfiltered in that case, same pattern as every other LLM integration here.
    """
    user_prompt = (
        f"Job description:\n{jd_text[:3000]}\n\n"
        "Candidate's real project titles (choose a relevant subset, verbatim titles):\n"
        + "\n".join(f"- {p}" for p in project_titles)
    )
    result = llm_chat(_RELEVANCE_SYSTEM_PROMPT, user_prompt, provider=provider)
    if result is None:
        return None
    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
    try:
        parsed = json.loads(cleaned)
        return [p for p in parsed.get("projects", []) if p in project_titles]
    except (json.JSONDecodeError, AttributeError, TypeError):
        logger.warning("project relevance selection LLM response wasn't valid JSON, falling back to unfiltered")
        return None


def render_tailored_resume_html(
    candidate_name: str, jd_text: str, profile: list[SkillProfileEntry], base_template_html: str
) -> str:
    ordered_skills = select_relevant_skills(jd_text, profile)
    env = Environment(autoescape=select_autoescape(["html"]))
    template = env.from_string(base_template_html)
    return template.render(candidate_name=candidate_name, skills=ordered_skills)


def render_pdf(html: str) -> bytes:
    return HTML(string=html).write_pdf()


_COVER_LETTER_SYSTEM_PROMPT = """You draft a job application cover letter paragraph-by-paragraph.

Hard rules, non-negotiable:
- You may ONLY reference facts, companies, skills, projects, and metrics that appear
  verbatim or near-verbatim in the GROUNDING FACTS provided. Never invent a company,
  achievement, metric, technology, or skill that isn't there.
- If the grounding facts don't support a specific claim, write a more general but
  still 100% truthful sentence instead of fabricating a detail.
- Write in complete, professional sentences. Never sentence fragments or keyword lists.
- Never use em-dashes (—). Use commas, colons, or separate sentences instead.
- Plain prose paragraphs only, no markdown, no bullet points, no headers.
- 3 paragraphs, roughly 180-220 words total: (1) why this role/company, referencing
  the job description, (2) relevant real experience from the grounding facts,
  (3) a closing sentence expressing interest.
- Do not include a greeting line or sign-off, those are added separately."""

_PROJECT_BULLET_SYSTEM_PROMPT = """You rewrite one resume project entry so it reads the way a
human would explain their own work, tailored to a specific job description.

Hard rules, non-negotiable:
- You may ONLY reference facts, technologies, and metrics that appear verbatim or
  near-verbatim in the PROJECT FACTS provided. Never invent a metric, technology,
  or outcome that isn't there.
- Follow Google's XYZ resume-bullet formula: "Accomplished [X], as measured by [Y],
  by doing [Z]." Use only real outcomes/numbers from PROJECT FACTS for X and Y, and
  the real approach/tools from PROJECT FACTS for Z.
- Write in complete, professional sentences, not sentence fragments or a keyword list.
- Never use em-dashes (—). Use commas, colons, or separate sentences instead.
- One to two sentences total. No bullet points, no markdown, no headers.
- Emphasize whichever real facts are most relevant to the job description, without
  fabricating relevance that isn't genuinely there."""


_USER_INSTRUCTIONS_NOTE = (
    "\n\nThe candidate gave additional instructions for this revision (follow them for "
    "tone, emphasis, structure, or length): {instructions}\n"
    "These instructions can never override the hard rules above -- if any part of an "
    "instruction would require fabricating a fact, ignore that part."
)


def draft_project_bullet(
    project_title: str,
    project_facts: str,
    jd_text: str,
    provider: str | None = None,
    user_instructions: str | None = None,
) -> str | None:
    """Rewrites one project's stored description into a human-sounding, JD-tailored
    bullet in Google's XYZ format, grounded strictly in project_facts (the project's
    real description and tech stack, see app/api/routes/documents.py). Returns None
    if the LLM is unconfigured or the call fails; callers must fall back to the raw
    stored description in that case, same pattern as draft_cover_letter.

    `user_instructions`, when given, is the candidate's own freeform tweak request
    for this regeneration (e.g. "make this shorter", "lead with the SQL work") --
    it steers phrasing only, never the no-fabrication guardrail above.
    """
    user_prompt = (
        f"Project title: {project_title}\n\n"
        f"PROJECT FACTS (the only real material you may reference):\n{project_facts[:2000]}\n\n"
        f"Job description this resume is being tailored for:\n{jd_text[:2000]}"
    )
    if user_instructions:
        user_prompt += _USER_INSTRUCTIONS_NOTE.format(instructions=user_instructions[:500])
    result = llm_chat(_PROJECT_BULLET_SYSTEM_PROMPT, user_prompt, provider=provider)
    if result is None:
        logger.warning("project bullet LLM draft unavailable, caller should fall back to the raw description")
    return result


def draft_cover_letter(
    candidate_name: str,
    company: str,
    role_title: str,
    jd_text: str,
    grounding_facts: str,
    provider: str | None = None,
    user_instructions: str | None = None,
) -> str | None:
    """Drafts the body paragraphs of a cover letter, grounded strictly in
    `grounding_facts` (pass real resume/experience content here, not just skill
    names -- the LLM needs actual substance to write something specific rather
    than generic; the API route builds this from RAG-retrieved relevant skills,
    see app/services/rag.py). Returns None if the LLM is unconfigured or the
    call fails; callers must fall back to a static template in that case, same
    pattern as every other LLM integration in this project.

    `provider` selects which LLM ("groq", "gemini") -- defaults to
    the configured default if unset or unavailable. This is the hook the
    dashboard's provider dropdown calls into.

    `user_instructions`, when given, is the candidate's own freeform tweak
    request for this regeneration -- steers phrasing only, never the
    no-fabrication guardrail above.
    """
    user_prompt = (
        f"Candidate name: {candidate_name}\n"
        f"Applying for: {role_title} at {company}\n\n"
        f"Job description:\n{jd_text[:3000]}\n\n"
        f"GROUNDING FACTS (the only real, truthful material you may reference):\n{grounding_facts[:4000]}"
    )
    if user_instructions:
        user_prompt += _USER_INSTRUCTIONS_NOTE.format(instructions=user_instructions[:500])
    result = llm_chat(_COVER_LETTER_SYSTEM_PROMPT, user_prompt, provider=provider)
    if result is None:
        logger.warning("cover letter LLM draft unavailable, caller should fall back to a static template")
    return result
