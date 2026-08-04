import numpy as np
from app.services.vector_store import add_to_index, search_index, save_index_and_meta, DATA_DIR, INDEX_PATH, META_PATH
import os
import json


def _cleanup():
    for p in [INDEX_PATH, META_PATH]:
        if p.exists():
            p.unlink()


def test_add_and_search():
    _cleanup()
    try:
        dim = 4
        embeddings = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
        chunk_ids = ["c1", "c2", "c3"]
        total = add_to_index(embeddings, chunk_ids, "doc1")
        assert total == 3

        results = search_index([1.0, 0.0, 0.0, 0.0], top_k=2, score_threshold=0.0)
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "c1"
    finally:
        _cleanup()


def test_search_empty_index():
    _cleanup()
    results = search_index([1.0, 0.0, 0.0, 0.0], top_k=5)
    assert results == []


def test_document_filter():
    _cleanup()
    try:
        emb1 = [[1.0, 0.0, 0.0, 0.0]]
        emb2 = [[0.9, 0.1, 0.0, 0.0]]
        add_to_index(emb1, ["c1"], "doc1")
        add_to_index(emb2, ["c2"], "doc2")

        results = search_index([1.0, 0.0, 0.0, 0.0], top_k=5, document_id="doc2", score_threshold=0.0)
        assert all(r["chunk_id"] != "c1" for r in results)
    finally:
        _cleanup()
