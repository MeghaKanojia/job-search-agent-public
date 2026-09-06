from pipeline.connectors.base import JobPosting
from pipeline.keyword_filter import matches_filters

ROLE_KEYWORDS = ["Data Engineer", "Data Analyst", "Data Scientist", "AI Engineer", "ML Engineer"]


def _posting(title: str) -> JobPosting:
    return JobPosting(source="test", title=title, url="https://example.com")


def test_exact_configured_phrase_matches():
    assert matches_filters(_posting("Senior Data Engineer"), ROLE_KEYWORDS)


def test_differently_titled_equivalent_role_matches():
    # The original spec explicitly asks for "similar roles even if they have
    # different titles" -- these have none of the exact configured phrases.
    assert matches_filters(_posting("Data Platform Engineer"), ROLE_KEYWORDS)
    assert matches_filters(_posting("BI Analyst"), ROLE_KEYWORDS)
    assert matches_filters(_posting("Machine Learning Scientist"), ROLE_KEYWORDS)
    assert matches_filters(_posting("Analytics Consultant Engineer"), ROLE_KEYWORDS)


def test_short_qualifier_does_not_false_positive_as_substring():
    # "ai" is a substring of "Maintenance" -- must not match without a word boundary.
    assert not matches_filters(_posting("Maintenance Engineer"), ROLE_KEYWORDS)
    assert not matches_filters(_posting("Retail Sales Developer"), ROLE_KEYWORDS)


def test_unrelated_role_does_not_match():
    assert not matches_filters(_posting("Warehouse Operative"), ROLE_KEYWORDS)
    assert not matches_filters(_posting("Sales Engineer"), ROLE_KEYWORDS)
