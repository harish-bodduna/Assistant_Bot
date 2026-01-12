"""
End-to-end Markdown -> Qdrant -> vLLM multimodal flow.

Features:
- Parses Markdown steps formatted as "# Step N" with inline images "![alt](url)".
- Embeds step text (sentence-transformers if available, else zeros) and upserts to Qdrant.
- Retrieves the top step for a user question and calls local vLLM (OpenAI-compatible)
  with interleaved text and image_url content.
"""

from __future__ import annotations

import argparse
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import APIError, APITimeoutError, OpenAI
from qdrant_client import QdrantClient, models

# Optional sentence-transformer for embeddings
try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore


# Configuration
COLLECTION = "mfa_guides"
MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
DEFAULT_DIM = 384  # matches all-MiniLM-L6-v2; used for zero-vector fallback

# Regex patterns
STEP_RE = re.compile(r"^#{1,6}\s*Step\s*(\d+)\s*(?::\s*(.+))?$", re.IGNORECASE)
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# Model clients
client = OpenAI(base_url=VLLM_BASE_URL, api_key="null")
_embedder: Optional["SentenceTransformer"] = None
_embed_dim: int = DEFAULT_DIM


def load_embedder() -> None:
    """Load sentence-transformer if available and set embed dimension."""
    global _embedder, _embed_dim
    if SentenceTransformer is None:
        return
    try:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        _embed_dim = _embedder.get_sentence_embedding_dimension()
    except Exception:
        _embedder = None
        _embed_dim = DEFAULT_DIM


def embed(text: str) -> List[float]:
    """Return an embedding vector for text or a zero-vector fallback."""
    if _embedder:
        return _embedder.encode([text])[0].tolist()
    return [0.0] * _embed_dim


def parse_markdown(md_text: str) -> List[Dict[str, Any]]:
    """Parse markdown into ordered steps with text and image URLs."""
    steps: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw_line in md_text.splitlines():
        line = raw_line.strip()
        m = STEP_RE.match(line)
        if m:
            if current:
                steps.append(current)
            step_num = int(m.group(1))
            title = (m.group(2) or "").strip()
            current = {"step": step_num, "title": title, "text_lines": [], "images": []}
            continue
        if current is None:
            continue
        img = IMG_RE.search(line)
        if img:
            current["images"].append(img.group(1))
        else:
            current["text_lines"].append(line)
    if current:
        steps.append(current)

    steps.sort(key=lambda s: s["step"])
    for s in steps:
        s["text"] = "\n".join([ln for ln in s["text_lines"] if ln]).strip()
    return steps


def ensure_collection(client: QdrantClient) -> None:
    """Create collection if missing."""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION in collections:
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=_embed_dim, distance=models.Distance.COSINE),
    )


def ingest_markdown(path: str) -> None:
    """Ingest a markdown file into Qdrant as step-level points."""
    md_text = Path(path).read_text(encoding="utf-8")
    steps = parse_markdown(md_text)
    if not steps:
        print(f"No steps found in {path}")
        return

    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    ensure_collection(qc)

    points: List[models.PointStruct] = []
    for s in steps:
        vec = embed(s["text"])
        payload = {
            "step": s["step"],
            "title": s.get("title", ""),
            "text": s["text"],
            "image_urls": s.get("images", []),
            "source_md": str(path),
        }
        points.append(models.PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload))

    try:
        qc.upsert(collection_name=COLLECTION, points=points)
        print(f"Ingested {len(points)} steps into {COLLECTION} from {path}")
    except Exception as exc:  # pragma: no cover - external IO
        print(f"Failed to upsert into Qdrant: {exc}")


def search_steps(query: str, k: int = 3) -> List[models.ScoredPoint]:
    """Search Qdrant for top-k steps."""
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    qvec = embed(query)
    try:
        res = qc.http.search_api.search_points(
            collection_name=COLLECTION,
            search_request=models.SearchRequest(
                vector=qvec,
                limit=k,
                with_payload=True,
            ),
        )
        return list(res.result or [])
    except Exception as exc:  # pragma: no cover - external IO
        raise RuntimeError(f"Qdrant search failed: {exc}") from exc


def answer_question(question: str, top_k: int = 1, timeout: float = 30.0) -> str:
    """Retrieve best step and query vLLM with text + image URLs."""
    try:
        hits = search_steps(question, k=top_k)
    except Exception as exc:
        return str(exc)

    if not hits:
        return "No matching steps found."

    top = hits[0]
    payload = top.payload or {}
    text = payload.get("text", "")
    images = payload.get("image_urls", []) or []

    content = [{"type": "text", "text": f"User question: {question}\n\nStep:\n{text}"}]
    for url in images[:20]:
        content.append({"type": "image_url", "image_url": {"url": url}})

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": content}],
            temperature=0.2,
            timeout=timeout,
        )
        return resp.choices[0].message.content
    except APITimeoutError:
        return "vLLM request timed out."
    except APIError as exc:
        return f"vLLM API error: {exc}"
    except Exception as exc:
        return f"vLLM error: {exc}"


def main() -> None:
    load_embedder()
    parser = argparse.ArgumentParser(description="Markdown -> Qdrant -> vLLM multimodal helper")
    parser.add_argument("--ingest", help="Path to Markdown file with # Step N sections")
    parser.add_argument("--ask", help="Question to query after retrieval")
    parser.add_argument("--top-k", type=int, default=1, help="Number of steps to retrieve")
    args = parser.parse_args()

    if args.ingest:
        ingest_markdown(args.ingest)
    if args.ask:
        answer = answer_question(args.ask, top_k=args.top_k)
        print("\nAnswer:\n", answer)


if __name__ == "__main__":
    main()

