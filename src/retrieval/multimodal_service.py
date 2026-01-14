from __future__ import annotations

import os
import re
import time
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
    Updated system prompt matching the notebook approach.
    """
    return (
        """You are the 1440 Foods Technical Documentation Reconstructor. You reconstruct a step-by-step technical guide from visual inputs.
        
        Inputs you will receive:
        PAGE MAPS: full-page document images (used to infer structure, title, step order, and layout/grid sequencing).
        HIGH-RES ASSETS: cropped screenshots/images extracted from the document (used as the primary visuals to attach to steps).
        
        Goal
        Given a user question plus the visual inputs, produce a clean instructional guide where each step's text is immediately followed by the most relevant HIGH‑RES ASSET SAS URL(s).
        
        Core rules (must follow)
        Use PAGE MAPS for ordering only
        Use the page maps to determine the correct reading/step sequence (including multi-column layouts and grids). Do not assume simple top-to-bottom order if the layout implies numbered/grouped steps.
        
        Action <-> Image binding is required
        For every instruction/step you output, attach the best matching HIGH‑RES ASSET URL immediately after the step text using markdown image syntax: ![Step description](FULL_SAS_URL)
        
        IMPORTANT: Always use markdown image syntax format: ![alt text](url). Never output plain URLs. Use format like: ![Step 1 Visual](https://...)
        
        If multiple images are needed for the same step, include multiple markdown image links under that step.
        If no suitable high-res asset exists, still output the step and write exactly: "Visual not available."
        Literal URL passthrough (critical)
        Do not modify SAS URLs in any way. Copy them exactly, including everything after ?. But always wrap them in markdown image syntax: ![description](FULL_SAS_URL)
        
        No administrative noise
        Exclude headers, footers, page numbers, logos, revision tables, document control metadata, legal disclaimers—unless they are explicitly part of the procedure.
        
        No external knowledge / no guessing
        Only use what is visible in the provided images.
        
        If text is unreadable and no clearer high-res asset exists: write exactly "Instruction unreadable in source."
        If the user's request cannot be answered from the visuals: provide this fallback contact info only: ITsupport@1440foods.com or (646) 809-0885.
        Do not reveal internal reasoning
        Do not describe your chain-of-thought. Output only the final guide.
        
        Matching guidance (how to choose the right asset)
        Prefer HIGH‑RES ASSETS that:
        
        contain the exact UI region referenced by the step,
        show the key button/field/menu named in the step,
        match the same page/section as the step (when inferable from layout).
        """
    )


def _build_page_maps_and_assets_content(
    page_sas_urls: dict,
    clean_images: List[Dict[str, Any]],
    user_query: str,
    max_images: int = 10,
) -> List[Dict[str, Any]]:
    """
    Build content structure: PAGE MAPS first, then HIGH-RES ASSETS manifest.
    Matches the notebook approach.
    """
    user_content: List[Dict[str, Any]] = []
    
    # Lead with Page Maps for Structure
    user_content.append({"type": "text", "text": "### INPUT TYPE 1: PAGE MAPS (STRUCTURE & LAYOUT)"})
    
    for page_no, url in sorted(page_sas_urls.items()):
        user_content.append({
            "type": "image_url",
            "image_url": {"url": url, "detail": "high"}
        })
    
    # Add the High-Res Asset Manifest
    asset_manifest = "\n### INPUT TYPE 2: HIGH-RES ASSETS (INDIVIDUAL SCREENSHOTS)\n"
    
    for img in clean_images[:max_images]:
        asset_manifest += f"Asset_ID: {img.get('id', 'unknown')} | Found on Page: {img.get('page', 0)}\nURL: {img.get('sas_url', '')}\n\n"
    
    user_content.append({
        "type": "text",
        "text": f"{asset_manifest}\n\n--- REASONING ENFORCEMENT ---\nBefore answering, analyze the grid layout in the Page Maps. Identify Step and explanations.\n\nUSER QUERY: {user_query}"
    })
    
    return user_content


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
    Inference coordinator with new page maps + high-res assets approach.
    """
    settings = get_settings()
    text_hit = retrieved_context.get("text")
    if not text_hit:
        return "No context found for the query."

    meta = text_hit.get("metadata") or {}
    
    # NEW: Get page images and clean images from metadata
    page_sas_urls = meta.get("page_images") or {}
    clean_images = meta.get("clean_images") or []
    
    # Fallback to old approach if new data not available
    if not page_sas_urls and not clean_images:
        sas_urls = retrieved_context.get("sas_urls") or []
        full_md = text_hit.get("markdown") or ""
        interleaved_content = _interleave_markdown_content(full_md, sas_urls=sas_urls, max_images=10, image_detail="low")
        if sas_urls:
            mapping_text = "Reference SAS URLs:\n" + "\n".join(f"- {u}" for u in sas_urls[:10])
            interleaved_content.insert(0, {"type": "text", "text": mapping_text})
    else:
        # NEW: Use page maps + high-res assets approach
        user_content = _build_page_maps_and_assets_content(
            page_sas_urls=page_sas_urls,
            clean_images=clean_images,
            user_query=user_query,
            max_images=10,
        )
        interleaved_content = user_content

    system_prompt = _get_system_prompt()

    # Primary: OpenAI GPT-5.2 snapshot
    if settings.openai_api_key and (not settings.openai_api_base or "localhost" not in settings.openai_api_base):
        attempts = 3
        last_err = None
        for attempt in range(attempts):
            try:
                ts_print(
                    f"Attempting primary inference with GPT-5.2 "
                    f"(base={settings.openai_api_base or 'https://api.openai.com'}), "
                    f"attempt {attempt + 1}/{attempts}"
                )
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_api_base or None,
                )
                
                # Convert to API format matching notebook structure
                api_content = []
                for item in interleaved_content:
                    if item.get("type") == "text":
                        api_content.append({"type": "input_text", "text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        # Flatten the nested dict to just a string URL
                        url = item.get("image_url", {}).get("url") if isinstance(item.get("image_url"), dict) else item.get("image_url")
                        if url:
                            api_content.append({"type": "input_image", "image_url": url})
                
                response = client.responses.create(
                    model="gpt-5.2",
                    instructions=system_prompt,
                    input=[
                        {
                            "type": "message",
                            "role": "user",
                            "content": api_content
                        }
                    ],
                    reasoning={
                        "effort": "high",
                        "summary": "auto",
                    },
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
                # Restore SAS tokens if needed
                sas_urls = meta.get("sas_urls") or []
                full_md = text_hit.get("markdown") or ""
                answer = _restore_sas_tokens(answer, sas_urls, full_md)
                _write_model_answer(text_hit, answer)
                ts_print("Primary inference succeeded (OpenAI GPT-5.2)")
                return answer
            except Exception as e:
                last_err = e
                ts_print(f"GPT-5.2 failed on attempt {attempt + 1}/{attempts}: {e}")
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

