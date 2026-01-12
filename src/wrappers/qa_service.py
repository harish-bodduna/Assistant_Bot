from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from src.retrieval.multimodal_service import get_1440_response, hybrid_search


def ts_print(msg: str) -> None:
    print(f"[{datetime.now().isoformat()}] {msg}")


def answer_question(user_query: str) -> Dict[str, Any]:
    """
    Thin wrapper to perform retrieval + inference and return a structured dict.
    """
    ts_print(f"Answering query: {user_query}")
    try:
        retrieval_data = hybrid_search(user_query)
    except Exception as exc:
        ts_print(f"Retrieval error: {exc}")
        return {
            "ok": False,
            "message": f"Retrieval error: {exc}",
            "answer_markdown": None,
            "source_file": None,
            "confidence_score": 0.0,
        }

    if not retrieval_data.get("text"):
        ts_print("No relevant manual found.")
        return {
            "ok": False,
            "message": retrieval_data.get("error") or "No relevant manual found for this query.",
            "answer_markdown": None,
            "source_file": None,
            "confidence_score": 0.0,
        }

    try:
        ts_print("Running multimodal inference")
        grounded_answer = get_1440_response(user_query, retrieval_data)
    except Exception as exc:
        ts_print(f"Inference error: {exc}")
        return {
            "ok": False,
            "message": f"Inference error: {exc}",
            "answer_markdown": None,
            "source_file": retrieval_data["text"]["metadata"].get("file_name"),
            "confidence_score": retrieval_data["text"].get("score", 0.0),
        }

    return {
        "ok": True,
        "message": "Success",
        "answer_markdown": grounded_answer,
        "source_file": retrieval_data["text"]["metadata"].get("file_name"),
        "confidence_score": retrieval_data["text"].get("score", 0.0),
    }

