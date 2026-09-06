from app.services.tailoring import SkillProfileEntry, select_relevant_skills


def test_never_adds_a_skill_outside_the_profile():
    profile = [
        SkillProfileEntry("Python", "language", "Built ETL pipelines in Python"),
        SkillProfileEntry("SQL", "language", "Wrote analytical queries"),
    ]
    jd_text = "We need someone strong in Python, SQL, Databricks, Snowflake, and Rust."

    result = select_relevant_skills(jd_text, profile)

    result_names = {s.skill_name for s in result}
    profile_names = {s.skill_name for s in profile}
    assert result_names <= profile_names, "tailoring must never surface a skill outside the truthful profile"
    assert "Databricks" not in result_names
    assert "Snowflake" not in result_names
    assert "Rust" not in result_names


def test_matched_skills_are_prioritized_first():
    profile = [
        SkillProfileEntry("Excel", "tool", None),
        SkillProfileEntry("Python", "language", None),
    ]
    jd_text = "Looking for a Python developer."

    result = select_relevant_skills(jd_text, profile)

    assert result[0].skill_name == "Python"
