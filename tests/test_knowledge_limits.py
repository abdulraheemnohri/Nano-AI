from nano import knowledge
import pytest

def test_punctuation_free_knowledge_is_split_into_bounded_chunks(monkeypatch):
    inserted = []
    monkeypatch.setattr(knowledge, "run", lambda sql, args=(): inserted.append((sql, args)))
    count = knowledge.ingest(("word " * 1600).strip())
    chunks = [args[1] for sql, args in inserted if "INSERT INTO memories" in sql]
    assert count == len(chunks)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= knowledge.MAX_CHUNK_CHARS for chunk in chunks)

def test_knowledge_import_rejects_oversized_text_before_writing(monkeypatch):
    writes = []
    monkeypatch.setattr(knowledge, "run", lambda *args: writes.append(args))
    with pytest.raises(ValueError, match="limited to"):
        knowledge.ingest("x" * (knowledge.MAX_INGEST_CHARS + 1))
    assert writes == []

def test_knowledge_import_rejects_excessive_chunk_count_before_writing(monkeypatch):
    writes = []
    monkeypatch.setattr(knowledge, "run", lambda *args: writes.append(args))
    source = " ".join("This is a sufficiently long sentence." for _ in range(knowledge.MAX_CHUNKS + 1))
    with pytest.raises(ValueError, match="chunks; limit is"):
        knowledge.ingest(source)
    assert writes == []
