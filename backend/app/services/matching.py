"""Rule-based keyword-overlap scoring between a job posting and your skill profile.

This is the v1 scorer (also mirrored in pipeline/databricks/notebooks/03_gold_scored_matches.py
for the batch/Databricks path). Deliberately simple and explainable, an MLflow-tracked
model can replace it later once enough labeled outcomes (applied/interview/rejected) exist.
"""

import re

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}")

# A single job posting was never going to mention most of a 70-item skill profile --
# dividing by the full profile size made even a genuinely strong match (5-6 real
# overlapping skills) score near zero. Scoring against a small fixed bar instead:
# this many matched skills (or more) counts as a full/strong match (1.0), so 2-3
# matches already read as a meaningfully high score rather than being buried near 0.
STRONG_MATCH_SKILL_COUNT = 5


def extract_keywords(text: str) -> set[str]:
    # rstrip trailing '.' -- it's allowed mid-token (for "Node.js", "3.11") but a
    # skill mentioned at the end of a sentence ("Proficiency in Python.") would
    # otherwise extract as "python." and silently fail to match "python".
    return {w.lower().rstrip(".") for w in _WORD_RE.findall(text or "")}


def score_posting(description: str, skill_names: list[str]) -> tuple[float, list[str]]:
    """Returns (score in [0,1], matched skill names) for a posting description
    against a flat list of the user's active skill names.
    """
    posting_words = extract_keywords(description)
    matched = [skill for skill in skill_names if skill.lower() in posting_words]
    if not skill_names:
        return 0.0, []
    score = len(matched) / STRONG_MATCH_SKILL_COUNT
    return round(min(score, 1.0), 4), matched
