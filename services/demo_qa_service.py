"""Demo QA business logic service - loads markdown from local file, uses pre-written answers."""
import asyncio
import json
import re
from pathlib import Path
from typing import AsyncGenerator
from src.retrieval.multimodal_service import get_demo_response
from services.streaming_service import stream_markdown_chunks


def load_mfa_markdown() -> str:
    """
    Load the manually edited MFA markdown from local file.

    Returns:
        Contents of llm_ready_sas_markdown.md file, or empty string if not found
    """
    markdown_file = Path("markdown_exports/mfa_manual_edit/llm_ready_sas_markdown.md")

    if not markdown_file.exists():
        return ""

    try:
        return markdown_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to read markdown from {markdown_file}: {e}")
        return ""


def load_wifi_guide_markdown() -> str:
    """
    Load the manually edited WiFi Guide markdown from local file.

    Returns:
        Contents of wifi_guide_llm_ready_markdown.md file, or empty string if not found
    """
    markdown_file = Path("markdown_exports/wifi_guide_manual_edit/wifi_guide_llm_ready_markdown.md")

    if not markdown_file.exists():
        return ""

    try:
        return markdown_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to read markdown from {markdown_file}: {e}")
        return ""


def load_app_protection_markdown() -> str:
    """
    Load the manually edited App Protection Policy markdown from local file.

    Returns:
        Contents of app_protection_llm_ready_markdown.md file, or empty string if not found
    """
    markdown_file = Path("markdown_exports/app_protection_manual_edit/app_protection_llm_ready_markdown.md")

    if not markdown_file.exists():
        return ""

    try:
        return markdown_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to read markdown from {markdown_file}: {e}")
        return ""


def select_document(question: str) -> str:
    """
    Select which document to load based on user query keywords.

    Args:
        question: User's question

    Returns:
        Document selection: 'mfa', 'wifi', or 'app_protection'
    """
    question_lower = question.lower()

    # MFA-related keywords
    mfa_keywords = [
        "multi.*factor.*authentication", "mfa", "multifactor.*authentication",
        "authentication.*steps", "microsoft.*authenticator", "authenticator.*app"
    ]

    # WiFi-related keywords
    wifi_keywords = [
        "wifi", "network", "connect", "connection", "password", "credentials",
        "wifi.*steps", "wifi.*connect", "wifi.*password", "wifi.*credentials",
        "wireless", "internet.*connect"
    ]

    # App Protection-related keywords
    app_protection_keywords = [
        "app.*protection", "application.*protection", "mobile.*app.*security",
        "device.*management", "intune", "app.*policy", "mobile.*device.*policy",
        "app.*security", "mobile.*application.*management"
    ]

    # Check for MFA keywords
    for keyword in mfa_keywords:
        if re.search(keyword, question_lower, re.IGNORECASE):
            return "mfa"

    # Check for WiFi keywords
    for keyword in wifi_keywords:
        if re.search(keyword, question_lower, re.IGNORECASE):
            return "wifi"

    # Check for App Protection keywords
    for keyword in app_protection_keywords:
        if re.search(keyword, question_lower, re.IGNORECASE):
            return "app_protection"

    # Default to MFA if no matches
    return "mfa"


def load_selected_markdown(document_type: str) -> str:
    """
    Load the appropriate markdown based on document type.

    Args:
        document_type: 'mfa', 'wifi', or 'app_protection'

    Returns:
        Markdown content or empty string if not found
    """
    if document_type == "wifi":
        return load_wifi_guide_markdown()
    elif document_type == "app_protection":
        return load_app_protection_markdown()
    else:  # default to MFA
        return load_mfa_markdown()


async def process_demo_question_stream(question: str) -> AsyncGenerator[str, None]:
    """
    Demo QA flow that loads markdown from local file based on query keywords.

    Flow:
    1. Analyze question to determine which document to use (MFA or WiFi)
    2. Load the selected llm_ready_sas_markdown from appropriate folder
    3. Call OpenAI with the markdown (which should return it unchanged)
    4. Stream the response as SSE chunks

    Args:
        question: User's question

    Yields:
        SSE-formatted strings with markdown chunks
    """
    try:
        # 1. Select document based on query
        selected_doc = select_document(question)
        print(f"Demo QA: Selected document '{selected_doc}' for query: {question[:50]}...")

        # 2. Load markdown from selected document
        llm_ready_sas_markdown = load_selected_markdown(selected_doc)

        if not llm_ready_sas_markdown:
            error_msg = f"Demo markdown file not found for {selected_doc} document"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            return

        # 3. Call OpenAI (should return the same markdown)
        loop = asyncio.get_event_loop()
        answer_markdown = await loop.run_in_executor(
            None,
            get_demo_response,
            question,
            llm_ready_sas_markdown
        )

        if not answer_markdown:
            yield f"data: {json.dumps({'error': 'Failed to generate demo response'})}\n\n"
            return

        # 4. Stream markdown chunks
        async for chunk in stream_markdown_chunks(answer_markdown, llm_ready_sas_markdown=llm_ready_sas_markdown):
            yield chunk
            await asyncio.sleep(0.01)

    except Exception as e:
        # Stream error as SSE
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
