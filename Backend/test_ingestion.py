from app.services.extraction import extract_text_from_pdf
from app.services.chunking import chunk_text


def test_chunk_text_basic():
    text = "Hello world. " * 200
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 120


def test_chunk_text_empty():
    chunks = chunk_text("")
    assert chunks == []


def test_chunk_text_short():
    chunks = chunk_text("Short text.")
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_preserves_content():
    paragraphs = ["Paragraph one about algorithms."] * 50
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=30)
    joined = " ".join(chunks)
    assert "algorithms" in joined
