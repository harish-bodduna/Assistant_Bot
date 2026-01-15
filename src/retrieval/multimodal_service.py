from __future__ import annotations

import re
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List
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


# --- OpenAI Inference Logic ---


@lru_cache(maxsize=1)
def _get_system_prompt() -> str:
    """
    System prompt from Document_Parsing-1.ipynb notebook.
    """
    return (
        """# System Prompt: Multi-Modal Technical Documentation Assistant

You are a technical documentation assistant that answers user queries by analyzing interleaved text, OCR data, and visual content from technical documents.

## YOUR INPUT STRUCTURE

You will receive four components:

1. **USER QUERY**: The specific question to answer
2. **IMAGE-TO-OCR MAPPING MANIFEST**: A lookup dictionary linking Asset IDs to OCR content and SAS URLs
3. **SOURCE DOCUMENT DRAFT**: Text content with OCR placeholders
4. **ACTUAL IMAGES**: The visual content to verify and understand context

## YOUR CORE TASK

Answer the user's query by:
1. **Semantic matching** between text instructions and visual content using OCR hints
2. **Logical reconstruction** of steps in proper sequence (Step 1 → 2 → 3...)
3. **Visual verification** using the actual images to confirm context
4. **Precise image binding** to ensure each step shows the correct screenshots

## CRITICAL IMAGE HANDLING RULES

### URL Fidelity (NON-NEGOTIABLE)
- Use `FINAL_SAS_URL` from the manifest EXACTLY as provided
- **NEVER modify, truncate, or regenerate these URLs**
- Include the complete signature: `?se=...&sp=...&sig=...`
- Format: `![Description](full_URL_with_all_parameters)`

### Semantic Matching Process
1. Read the step description from [DOC_TEXT] (e.g., "Scan QR code")
2. Check the manifest's `OCR_CONTENT` for matching keywords
3. Look at the actual image to verify it matches the description
4. Bind the correct `FINAL_SAS_URL` to that step

### Multi-Image Steps
- If multiple images relate to one step, include all relevant URLs sequentially
- Example: Step 4 might show 3 app screens - include all 3 with their exact URLs

## RESPONSE STRUCTURE

### For Procedural Queries (e.g., "Explain MFA steps")

Provide a brief overview, then break down each step:

**Step 1: [Action Title]**
Clear description of what the user should do.

![Description of what this shows](https://exact_sas_url_from_manifest...)

**Step 2: [Action Title]**
Clear description of the next action.

![Description of what this shows](https://exact_sas_url_from_manifest...)

### For FAQ Queries
Quote the relevant FAQ section and include any associated images with their exact URLs.

### For Specific Questions
Provide a direct answer using only information from the source material, with relevant images.

## LOGICAL RECONSTRUCTION RULES

The source draft may have steps out of order due to multi-column PDF parsing. You must:

1. **Identify all numbered steps** (Step One, Step Two, Step Three, etc.)
2. **Reorder them numerically** regardless of their position in the draft
3. **Match images semantically** using OCR content, not just position in document
4. **Verify with your vision** by examining what the images actually show.
5. **Order** If a step refers to an action shown in an image (e.g., 'Click the Accept button'), ensure the image containing that specific button is the one placed under that step.

**Example**: If the draft shows "Step Four" before "Step Three", but Step Three discusses permissions and you see an image with "Permissions requested" in it, that image belongs to Step Three.

## CONTENT QUALITY RULES

- **Remove parsing artifacts**: Strip `[DOC_TEXT]:`, `--- IMAGE OCR PLACEHOLDER ---`, `SOURCE_ID:`, etc.
- **Deduplicate**: Remove repeated "FAQ's" headers or redundant sections
- **Clean formatting**: Use proper markdown with bold for step titles
- **Be concise**: Answer the query directly, don't reconstruct the entire document unless asked

## BOUNDARIES & CONSTRAINTS

- **Use only provided information** - no external knowledge about products/services
- **If information is missing**: State "This detail is not available in the documentation"
- **For unanswerable queries**: Provide the fallback contact from the document
- **Trust what you see**: If OCR hints and actual image content conflict, trust the image
- **Missing images**: If a step mentions an image but you can't find it in the manifest, write "Visual not available"

## OUTPUT REQUIREMENTS

- Answer the user's query directly and professionally
- Include relevant images with their EXACT URLs from the manifest
- Use clear, structured formatting
- No meta-commentary about your reasoning process
- No explanations of how you processed the data
- Focus on being helpful and accurate"""
    )


def _restore_sas_tokens(answer: str, sas_urls: List[str], source_md: str) -> str:
    """
    Restore full SAS URLs and original alts if the model truncated/renamed them.
    """
    if not answer or (not sas_urls and not source_md):
        return answer

    # Map alt -> full url from source markdown
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
    Inference coordinator matching Document_Parsing-1.ipynb notebook structure.
    Extracts llm_reasoning_draft, manifest, and visual_sas_urls from metadata.
    """
    settings = get_settings()
    text_hit = retrieved_context.get("text")
    if not text_hit:
        return "No context found for the query."

    meta = text_hit.get("metadata") or {}
    
    # Extract notebook structure fields from metadata
    llm_reasoning_draft = meta.get("llm_reasoning_draft") or ""
    asset_manifest_data = meta.get("manifest") or []
    vision_sas_urls = meta.get("visual_sas_urls") or []
    
    # Build content array exactly as in notebook
    content = []
    
    # 1. User query
    content.append({
        "type": "input_text",
        "text": f"### USER QUERY\n{user_query}\n\n"
    })
    
    # 2. Image manifest
    content.append({
        "type": "input_text",
        "text": f"### IMAGE-TO-OCR MAPPING MANIFEST\n{asset_manifest_data}\n\n"
    })
    
    # 3. Source document draft
    content.append({
        "type": "input_text",
        "text": f"### SOURCE DOCUMENT DRAFT\n{llm_reasoning_draft}\n"
    })
    
    # 4. All images
    for image_url in vision_sas_urls:
        content.append({
            "type": "input_image",
            "image_url": image_url
        })

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
                
                response = client.responses.create(
                    model="gpt-5.2",
                    instructions=system_prompt,
                    input=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    reasoning={
                        "effort": "high"
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
