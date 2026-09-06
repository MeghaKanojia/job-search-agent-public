from app.services.matching import score_posting

# A profile this size is realistic (see backend/db seed data) -- no single posting
# will ever mention most of it, so the score must not be computed against len(profile).
LARGE_PROFILE = [f"skillnum{i}" for i in range(70)]


def test_a_few_real_matches_score_meaningfully_high_not_near_zero():
    description = "We need someone strong in skillnum0, skillnum1, and skillnum2."

    score, matched = score_posting(description, LARGE_PROFILE)

    assert len(matched) == 3
    assert score >= 0.5, "3 real matches against a 70-item profile must not score near zero"


def test_five_or_more_matches_is_a_full_score():
    description = " ".join(f"skillnum{i}" for i in range(6))

    score, matched = score_posting(description, LARGE_PROFILE)

    assert len(matched) == 6
    assert score == 1.0


def test_no_matches_scores_zero():
    score, matched = score_posting("Completely unrelated posting text.", LARGE_PROFILE)

    assert matched == []
    assert score == 0.0
