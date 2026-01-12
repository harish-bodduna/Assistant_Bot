from __future__ import annotations

import argparse
from typing import List

import dspy

from src.optimization.dspy_rag import TroubleshootingProgram, configure_lm
from src.retrieval.full_doc import hybrid_search


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DSPy troubleshooting program over retrieved context.")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--top-k", type=int, default=1, help="Number of text hits to concatenate as context")
    args = parser.parse_args()

    configure_lm()
    program = TroubleshootingProgram()

    res = hybrid_search(args.query)
    text_hit = res.get("text") or {}
    md = text_hit.get("markdown") or ""
    context_parts: List[str] = []
    if md:
        context_parts.append(md)
    ctx = "\n\n".join(context_parts)

    pred = program(context=ctx, user_query=args.query)
    print(pred.interleaved_response)


if __name__ == "__main__":
    main()

