import json
import os
from pathlib import Path

import faiss
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INDEX_PATH = DATA_DIR / "faiss_index.bin"
META_PATH = DATA_DIR / "faiss_meta.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_index_and_meta() -> tuple[faiss.Index | None, list[dict]]:
    if INDEX_PATH.exists() and META_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "r") as f:
            meta = json.load(f)
        return index, meta
    return None, []


def save_index_and_meta(index: faiss.Index, meta: list[dict]):
    _ensure_dir()
    tmp_index = str(INDEX_PATH) + ".tmp"
    tmp_meta = str(META_PATH) + ".tmp"
    faiss.write_index(index, tmp_index)
    with open(tmp_meta, "w") as f:
        json.dump(meta, f)
    os.replace(tmp_index, str(INDEX_PATH))
    os.replace(tmp_meta, str(META_PATH))


def add_to_index(
    embeddings: list[list[float]],
    chunk_ids: list[str],
    document_id: str,
) -> int:
    vectors = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(vectors)

    index, meta = load_index_and_meta()
    if index is None:
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        meta = []

    start_pos = index.ntotal
    index.add(vectors)
    for i, cid in enumerate(chunk_ids):
        meta.append({"chunk_id": cid, "document_id": document_id, "position": start_pos + i})

    save_index_and_meta(index, meta)
    return index.ntotal


def search_index(
    query_embedding: list[float],
    top_k: int = 5,
    document_id: str | None = None,
    score_threshold: float = 0.3,
) -> list[dict]:
    index, meta = load_index_and_meta()
    if index is None or index.ntotal == 0:
        return []

    query = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query)

    search_k = min(top_k * 3, index.ntotal) if document_id else min(top_k, index.ntotal)
    distances, indices = index.search(query, search_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1 or dist < score_threshold:
            continue
        entry = meta[idx]
        if document_id and entry["document_id"] != document_id:
            continue
        results.append({"chunk_id": entry["chunk_id"], "score": float(dist)})
        if len(results) >= top_k:
            break

    return results
