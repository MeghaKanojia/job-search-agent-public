from app.services import rag


class _FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalars(self._items)


class _FakeDB:
    """Returns `sequence[call_count]` (clamped to the last entry) from execute()
    each time it's called, so a test can simulate "first query empty, fallback
    query has results" without depending on the actual SQL statement built.
    """

    def __init__(self, sequence):
        self._sequence = sequence
        self.call_count = 0

    def execute(self, stmt):
        idx = min(self.call_count, len(self._sequence) - 1)
        items = self._sequence[idx]
        self.call_count += 1
        return _FakeResult(items)


def test_falls_back_to_all_active_on_embedding_failure(monkeypatch):
    def raise_import_error(text_to_embed):
        raise ImportError("No module named 'fastembed'")

    monkeypatch.setattr(rag, "embed_text", raise_import_error)

    db = _FakeDB([["python-item", "sql-item"]])
    result = rag.retrieve_relevant_skills(db, "some JD text")

    assert result == ["python-item", "sql-item"]


def test_falls_back_when_no_embeddings_populated_yet(monkeypatch):
    monkeypatch.setattr(rag, "embed_text", lambda text_to_embed: [0.0] * 384)

    # First execute() call: the vector-similarity query, empty (no embeddings
    # backfilled yet). Second: the _all_active fallback query, has results.
    db = _FakeDB([[], ["python-item"]])

    result = rag.retrieve_relevant_skills(db, "some JD text")

    assert result == ["python-item"]
