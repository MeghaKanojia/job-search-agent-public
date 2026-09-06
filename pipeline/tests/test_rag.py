from pipeline import rag


def test_vector_literal_formatting_has_no_spaces():
    # pgvector's text input format is stricter about this in some versions
    # than Python's default str(list), which inserts a space after each comma.
    result = rag._vector_literal([0.1, 0.2, -0.3])
    assert result == "[0.1,0.2,-0.3]"
    assert " " not in result


class _FakeRow:
    def __init__(self, skill_name):
        self.skill_name = skill_name


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *a, **k):
        return _FakeResult(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeEngine:
    def __init__(self, rows):
        self._rows = rows

    def connect(self):
        return _FakeConn(self._rows)


def test_retrieve_relevant_skills_falls_back_to_all_active_on_embedding_failure(monkeypatch):
    # fastembed isn't installed in this environment (deliberately, to keep the
    # GitHub Actions/Render install light) -- embed_text() raising ImportError
    # must not crash ingestion, it must fall back to returning every active
    # skill name, same as if RAG had never been added.
    def raise_import_error(text_to_embed):
        raise ImportError("No module named 'fastembed'")

    monkeypatch.setattr(rag, "embed_text", raise_import_error)

    engine = _FakeEngine([_FakeRow("Python"), _FakeRow("SQL")])

    result = rag.retrieve_relevant_skills(engine, "some JD text")

    assert result == ["Python", "SQL"]


def test_retrieve_relevant_skills_falls_back_when_no_embeddings_populated_yet(monkeypatch):
    # Embedding succeeds, but the query returns zero rows because
    # backfill_skill_embeddings() hasn't been run yet -- must still fall back
    # to all active skills rather than silently retrieving nothing.
    monkeypatch.setattr(rag, "embed_text", lambda text_to_embed: [0.0] * 384)

    # Counter lives on the engine, not the connection -- retrieve_relevant_skills
    # calls engine.connect() twice (once for the vector query, once inside the
    # _all_active_skill_names fallback), each getting its own connection object.
    class _SwitchingConn:
        def __init__(self, engine):
            self._engine = engine

        def execute(self, *a, **k):
            self._engine.call_count += 1
            # First call overall: the vector-similarity query (no embeddings
            # backfilled yet -> empty). Second call: the fallback's plain query.
            if self._engine.call_count == 1:
                return _FakeResult([])
            return _FakeResult([_FakeRow("Python")])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _SwitchingEngine:
        def __init__(self):
            self.call_count = 0

        def connect(self):
            return _SwitchingConn(self)

    result = rag.retrieve_relevant_skills(_SwitchingEngine(), "some JD text")

    assert result == ["Python"]
