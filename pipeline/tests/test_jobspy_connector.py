import datetime as dt

import pandas as pd

from pipeline.connectors.jobspy_connector import _clean


def test_nan_becomes_none_not_the_literal_json_token():
    # A real ingestion run crashed on exactly this: a posting with no listed
    # company came back from JobSpy's underlying pandas DataFrame as NaN, which
    # serializes to the invalid JSON token `NaN` and Postgres rejected the insert.
    assert _clean(float("nan")) is None


def test_missing_date_becomes_none():
    assert _clean(pd.NaT) is None


def test_none_stays_none():
    assert _clean(None) is None


def test_real_string_value_is_preserved():
    assert _clean("Data Engineer") == "Data Engineer"


def test_real_date_value_is_preserved_as_a_date_not_stringified():
    today = dt.date(2026, 9, 4)
    assert _clean(today) == today


def test_numeric_id_is_stringified():
    assert _clean(12345) == "12345"
