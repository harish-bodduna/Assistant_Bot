from __future__ import annotations

import os
import re
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.config.settings import get_settings


def ts_print(msg: str) -> None:
    print(f"[{datetime.now().isoformat()}] {msg}")


# --- Embedding & Client Helpers ---


def get_text_embed():
    return HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _text_client_model():
    settings = get_settings()
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
    )
    model = get_text_embed()
    return client, model


# --- Retrieval Logic ---


def hybrid_search(query: str) -> Dict[str, Any]:
    """Layout-aware text retrieval with small-doc full markdown injection."""
    ts_print("Embedding query for text search")
    try:
        text_client, text_model = _text_client_model()
        q_vec = text_model.get_text_embedding(query)
        res = text_client.http.search_api.search_points(
            collection_name="manuals_text",
            search_request=models.SearchRequest(
                vector=q_vec,
                limit=1,
                with_payload=True,
            ),
        ).result
    except Exception as exc:
        ts_print(f"Qdrant text search failed: {exc}")
        return {
            "text": None,
            "sas_urls": [],
            "mode": "error",
            "error": f"Qdrant search failed: {exc}",
        }

    if not res:
        return {"text": None, "sas_urls": [], "mode": "none"}

    top = res[0]
    payload = top.payload or {}
    llm_md = (
        payload.get("llm_markdown")
        or payload.get("text")
        or payload.get("page_content")
        or payload.get("content")
        or ""
    )
    text_hit = {
        "markdown": llm_md,
        "metadata": payload,
        "score": top.score,
    }

    meta = text_hit["metadata"] or {}
    total_pages = meta.get("total_pages") or 0
    sas_urls = meta.get("sas_urls") or []
    file_name = meta.get("file_name")

    if total_pages and total_pages <= 10 and file_name:
        ts_print(f"Full-doc injection for {file_name} (<=10 pages)")
        return {"text": text_hit, "sas_urls": sas_urls, "mode": "full_doc"}

    return {"text": text_hit, "sas_urls": sas_urls, "mode": "chunk"}


# --- OpenAI & Fallback Inference Logic ---


def _interleave_markdown_content(
    full_md: str,
    sas_urls: Optional[List[str]] = None,
    max_images: int = 10,
    image_detail: str = "low",
) -> List[Dict[str, Any]]:
    """
    Parse Markdown and convert ![alt](url) into interleaved content blocks.
    Ensures the LLM sees images in-flow with the instructions.
    """
    pattern = r"(!\[[^\]]*\]\([^\)]+\))"
    parts = re.split(pattern, full_md)
    content_blocks: List[Dict[str, Any]] = []
    img_count = 0
    for part in parts:
        img_match = re.match(r"!\[[^\]]*\]\(([^\)]+)\)", part)
        if img_match:
            url = img_match.group(1).strip()
            if img_count < max_images:
                content_blocks.append(
                    {"type": "image_url", "image_url": {"url": url, "detail": image_detail}}
                )
                img_count += 1
        elif part.strip():
            content_blocks.append({"type": "text", "text": part})
    if sas_urls:
        for url in sas_urls:
            if img_count >= max_images:
                break
            content_blocks.append({"type": "image_url", "image_url": {"url": url, "detail": image_detail}})
            img_count += 1
    return content_blocks


def _to_response_content(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert interleaved text/image blocks to OpenAI Responses API schema.
    """
    content: List[Dict[str, Any]] = []
    for b in blocks:
        if b.get("type") == "text":
            content.append({"type": "input_text", "text": b.get("text", "")})
        elif b.get("type") == "image_url":
            url = None
            if isinstance(b.get("image_url"), dict):
                url = b.get("image_url", {}).get("url")
            else:
                url = b.get("image_url")
            if url:
                content.append({"type": "input_image", "image_url": url})
    return content


def _flatten_to_markdown(blocks: List[Dict[str, Any]]) -> str:
    """
    Flatten interleaved blocks into markdown (for text-only fallback models).
    """
    parts: List[str] = []
    for b in blocks:
        if b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif b.get("type") == "image_url":
            url = (
                b.get("image_url", {}).get("url")
                if isinstance(b.get("image_url"), dict)
                else b.get("image_url")
            )
            if url:
                parts.append(f"![Visual]({url})")
    return "\n".join(parts)


@lru_cache(maxsize=1)
def _get_system_prompt() -> str:
    """
    Cached system prompt; identical content reused for every call.
    """
    return (
        "SYSTEM ROLE: You are the 1440 Foods Technical Expert. Your goal is to convert complex, messy manual data into a clean, visual step-by-step guide along with images or screenshot (as URL) provided for clear explanation for a technician."
        "You are a professional technical expert. So respond to each question in polite, professional and user-friendly manner.\n\n"
        "CORE TASK: Extract only the functional instructions with associated IMAGES URLs from the provided context. Answer the user's query by creating an interleaved guide where ever every instruction is physically anchored to its relevant image.\n\n"
        "STRICT FILTERING RULES:\n"
        "1. DISCARD ADMINISTRATIVE NOISE: Do NOT include Table of Contents, Document Control, Approval Histories, Footer, Header or Cover Pages.\n"
        "2. ACTION-IMAGE BINDING: For every step or instruction you include, you MUST find the corresponding ![Step Visual](url) from the source and place it immediately after the text description. This is very important. We need images to be displaying on front end UI.\n"
        "3. MULTI-IMAGE PRESERVATION: If a single logical step (e.g., \"Set up MFA\") has multiple sequential images in the source, you MUST include all of them in the correct order. Do not condense multiple images into one.\n"
        "4. LITERAL URL PASSTHROUGH: You are forbidden from modifying the SAS URL strings. Copy them exactly, including all characters after the '?' symbol from URL.\n\n"
        "REASONING GUIDELINES:\n"
        "- Grounding: Use the physical proximity of images to text in the source to determine which image belongs to which instruction.\n"
        "- Clarity: If the source text is fragmented, rephrase it into clear, professional instructions, but NEVER lose the associated image.\n"
        "- Transparency: If the information requested is not in the text or visible in the screenshots, say: \"This specific detail is not covered in the available manual.\"\n\n"
        "OUTPUT FORMAT:\n"
        "### [Main Title of the Process]\n"
        "[Clear instructional sentence]\n"
        "![Visual](SAS_URL)\n"
        "...and so on.\n\n"
        "ANTI-HALLUCINATION RULES:\n"
        "- Contextual Isolation: Do NOT use outside knowledge about hardware or software (e.g., general Barracuda Backup specs). If the information is not in the provided text or images, state \"This information is not available in the manual.\"\n"
        "- Visual Confirmation: Before stating a fact found in an image (like a schedule or status), cross-reference it with the image's adjacent text. If they conflict, prioritize the visual information but note the discrepancy.\n"
        "- Negative Constraint: If a user asks for a specific value (like a 'Retention Policy') and it is not explicitly mentioned in the text or visible in the dashboard screenshots, do NOT infer or guess it based on typical industry standards.\n\n"
        "FALLBACK INSTRUCTION:\n"
        "- If the query cannot be answered using the provided context, provide the IT Support contact details from the end of the document: ITsupport@1440foods.com or (646) 809-0885."
    )


def _restore_sas_tokens(answer: str, sas_urls: List[str], source_md: str) -> str:
    """
    Restore full SAS URLs and original alts if the model truncated/renamed them.
    """
    if not answer or (not sas_urls and not source_md):
        return answer

    # Map alt -> full url from source markdown
    import re

    md_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", source_md or "")
    alt_to_full = {alt.strip(): url.strip() for alt, url in md_images}

    # Replace base matches with full SAS
    for sas in sas_urls:
        base = sas.split("?", 1)[0]
        if base in answer and sas not in answer:
            answer = answer.replace(base, sas)

    # Enforce alt/url pairs from source (handles renamed alts or shortened URLs)
    for alt, full in alt_to_full.items():
        base = full.split("?", 1)[0]
        # If model shortened URL, restore full
        answer = answer.replace(f"]({base})", f"]({full})")
        # If model kept URL but renamed alt, restore alt
        answer = answer.replace(f"]({full})", f"[{alt}]({full})")

    return answer


def get_1440_response(user_query: str, retrieved_context: Dict[str, Any]) -> str:
    """
    Inference coordinator:
    1. Primary: OpenAI GPT-4o
    2. Fallback: Local Qwen-VL via vLLM
    """
    settings = get_settings()
    text_hit = retrieved_context.get("text")
    if not text_hit:
        return "No context found for the query."

    sas_urls = retrieved_context.get("sas_urls") or []
    full_md = text_hit.get("markdown") or ""
    interleaved_content = _interleave_markdown_content(full_md, sas_urls=sas_urls, max_images=10, image_detail="low")
    # Semi-static mapping for SAS URLs (cached prefix) if URLs are stable enough
    if sas_urls:
        mapping_text = "Reference SAS URLs:\n" + "\n".join(f"- {u}" for u in sas_urls[:10])
        interleaved_content.insert(0, {"type": "text", "text": mapping_text})

    system_prompt = _get_system_prompt()

    # Messages ordered for cache friendliness: system + context (prefix), then dynamic query
    responses_input = [
        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        {"role": "user", "content": _to_response_content(interleaved_content)},  # cached prefix
        {"role": "user", "content": [{"type": "input_text", "text": f"Technician Query: {user_query}"}]},  # dynamic
    ]

    # Primary: OpenAI GPT-5.2 snapshot (skip if running local-only or missing key)
    if settings.openai_api_key and (not settings.openai_api_base or "localhost" not in settings.openai_api_base):
        attempts = 3
        last_err = None
        for attempt in range(attempts):
            try:
                ts_print(
                    f"Attempting primary inference with GPT-5.2-2025-12-11 "
                    f"(base={settings.openai_api_base or 'https://api.openai.com'}), "
                    f"attempt {attempt + 1}/{attempts}"
                )
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_api_base or None,
                )
                response = client.responses.create(
                    model="gpt-5.2-2025-12-11",
                    input=[
                        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                        {"role": "user", "content": _to_response_content(interleaved_content)},
                        {"role": "user", "content": [{"type": "input_text", "text": f"Technician Query: {user_query}"}]},
                    ],
                    temperature=0,
                    timeout=300,
                )
                # Log cache usage if available
                try:
                    usage = getattr(response, "usage", None)
                    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) if usage else 0
                    total = getattr(usage, "total_tokens", 0) if usage else 0
                    ts_print(f"Usage: {total} tokens total. Cache hit tokens: {cached}.")
                except Exception:
                    pass

                answer = response.output_text
                answer = _restore_sas_tokens(answer, sas_urls, full_md)
                _write_model_answer(text_hit, answer)
                ts_print("Primary inference succeeded (OpenAI GPT-5.2-2025-12-11)")
                return answer
            except Exception as e:
                last_err = e
                ts_print(f"GPT-5.2-2025-12-11 failed on attempt {attempt + 1}/{attempts}: {e}")
                if attempt < attempts - 1:
                    time.sleep(3)
                    continue
                return f"OpenAI primary error after retries: {last_err}"
    else:
        ts_print("Primary inference skipped (no API key or using localhost base)")
        return "OpenAI not configured: missing API key or using localhost base."


def _write_model_answer(text_hit: Dict[str, Any], answer: str) -> None:
    """
    Write model answer next to the exported markdown, if markdown_path is present.
    """
    md_path = text_hit.get("metadata", {}).get("markdown_path") or text_hit.get("metadata", {}).get("markdown")
    if not md_path:
        return
    try:
        p = Path(md_path)
        out_path = p.parent / "answer.md"
        out_path.write_text(answer or "", encoding="utf-8")
    except Exception:
        # Best-effort; ignore write failures
        return


if __name__ == "__main__":
    # Example usage for testing
    q = "How do I reset the printer?"
    ctx = hybrid_search(q)
    if ctx.get("text"):
        ans = get_1440_response(q, ctx)
        print("\n--- FINAL ANSWER ---\n")
        print(ans)
    else:
        print("No results found.")

