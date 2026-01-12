"""
Send SAS-bearing markdown + images to local vLLM (Qwen) using the required system prompt.

Usage:
  python -m src.cli.chat_with_sas --query "How do I access external SharePoint?"

Environment:
  VLLM_BASE_URL (default http://localhost:8000/v1)
  MODEL_NAME (default Qwen/Qwen2.5-VL-7B-Instruct)
"""

from __future__ import annotations

import argparse
import os
from typing import List

from openai import OpenAI
from src.retrieval.full_doc import hybrid_search  # noqa: E402


SYSTEM_PROMPT = """
You are the 1440 Foods Support Bot. You receive a technical manual with text and Azure SAS image links.

STRICT RULES:
- Preserve the Interleaved Markdown exactly as given.
- For every step you describe, you MUST place its image immediately after that step’s text.
- Use the exact ![Step Visual](URL) syntax from the source. Do not change or trim the SAS token (the part after ?).
- Never group images at the end. An instruction without its image right after it is incomplete.
- Do not summarize or reorder steps. Reflect the input order.
""".strip()


def build_messages(question: str, md: str, image_urls: List[str]) -> list:
    mapping = "\n".join([f"Image {i+1}: {u}" for i, u in enumerate(image_urls)])
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Preserve the exact interleaved order shown below. Do not regroup images.\n\n"
                        f"User question: {question}\n\n"
                        "Full markdown (source of truth):\n"
                        f"{md}\n\n"
                        "Numbered image mapping:\n"
                        f"{mapping}"
                    ),
                },
                *[
                    {"type": "image_url", "image_url": {"url": url}}
                    for url in image_urls[:20]
                ],
            ],
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Send SAS-markdown + images to local vLLM (Qwen)")
    parser.add_argument("--query", required=True, help="User question / retrieval query")
    parser.add_argument("--max-images", type=int, default=10, help="Max images to send (default 10, cap 20)")
    args = parser.parse_args()

    client = OpenAI(base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"), api_key="null")
    model = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-VL-7B-Instruct")

    res = hybrid_search(args.query)
    text_hit = res.get("text") or {}
    md = text_hit.get("markdown") or ""
    if not md:
        print("No markdown found for query.")
        return

    meta = text_hit.get("metadata") or {}
    figs = meta.get("fig_images") or []
    image_urls = [f.get("sas_url") for f in figs if f.get("sas_url")]
    if args.max_images:
        image_urls = image_urls[: min(args.max_images, 20)]

    messages = build_messages(args.query, md, image_urls)

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    print("Images sent:", len(image_urls))
    print(resp.choices[0].message.content)


if __name__ == "__main__":
    main()

