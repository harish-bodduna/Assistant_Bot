from __future__ import annotations

import asyncio
from typing import Any, Dict
from datetime import datetime

from src.orchestration.agent import build_1440_agent


def ts_print(msg: str) -> None:
    print(f"[{datetime.now().isoformat()}] {msg}")


def run_query(user_query: str) -> Dict[str, Any]:
    """
    Thin wrapper to run the orchestration agent end-to-end.
    """
    try:
        ts_print(f"Running agent for query: {user_query}")
        agent = build_1440_agent()
        # Use the inline run_query helper (no tool-calls)
        result = agent.run_query(user_query)  # type: ignore[attr-defined]
        payload: Dict[str, Any] = {}
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        elif isinstance(result, dict):
            payload = result
        else:
            payload = {"answer_markdown": str(result)}
        return {"ok": True, "message": "Success", **payload}
    except Exception as exc:
        ts_print(f"Agent error: {exc}")
        return {"ok": False, "message": f"Agent error: {exc}"}

