from __future__ import annotations

from typing import Optional

import os

from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.config.settings import get_settings
from src.retrieval.multimodal_service import get_1440_response, hybrid_search


class TechnicalResponse(BaseModel):
    """
    Final validated output for the UI.
    Contains the grounded answer with interleaved Markdown images.
    """

    answer_markdown: str = Field(..., description="The full interleaved text and image response")
    source_file: Optional[str] = Field(None, description="The primary manual used for the answer")
    confidence_score: float = Field(0.0, description="The retrieval score from Qdrant")


def build_1440_agent() -> Agent[TechnicalResponse]:
    """
    Creates the PydanticAI Agent that orchestrates the 1440 Support Bot.
    This variant runs directly on a single model (local Qwen or remote OpenAI)
    and performs retrieval + answer inline (no tool calls).
    """
    settings = get_settings()
    # Ensure downstream OpenAI provider picks up configured key/base.
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.openai_api_base:
        os.environ.setdefault("OPENAI_BASE_URL", settings.openai_api_base)

    agent_model = os.getenv("AGENT_MODEL", "gpt-5.2-flagship")
    agent = Agent(
        f"openai:{agent_model}",
        system_prompt=(
            "You are the 1440 Foods Support Orchestrator. "
            "Your job is to take technical queries, use the retrieval tool to get manual content, "
            "and produce a technician-ready guide. "
            "STRICT RULE: You must preserve interleaved SAS images (e.g., ![Visual](url)) "
            "exactly as they appear in the source context."
        ),
    )

    # Bind a simple run function onto the agent for convenience.
    # This avoids tool-calls; we do retrieval + inference inline.
    def _run_query(user_query: str) -> TechnicalResponse:
        logger.info(f"Agent resolving: {user_query}")

        try:
            retrieval_data = hybrid_search(user_query)
        except Exception as exc:
            return TechnicalResponse(
                answer_markdown=f"Retrieval error: {exc}",
                source_file=None,
                confidence_score=0.0,
            )

        if not retrieval_data.get("text"):
            err = retrieval_data.get("error")
            return TechnicalResponse(
                answer_markdown=err or "No relevant manual found for this query.",
                source_file=None,
                confidence_score=0.0,
            )

        try:
            grounded_answer = get_1440_response(user_query, retrieval_data)
            return TechnicalResponse(
                answer_markdown=grounded_answer,
                source_file=retrieval_data["text"]["metadata"].get("file_name"),
                confidence_score=retrieval_data["text"].get("score", 0.0),
            )
        except Exception as exc:
            return TechnicalResponse(
                answer_markdown=f"Inference error: {exc}",
                source_file=retrieval_data["text"]["metadata"].get("file_name"),
                confidence_score=retrieval_data["text"].get("score", 0.0),
            )

    agent.run_query = _run_query  # type: ignore[attr-defined]
    return agent


if __name__ == "__main__":
    agent = build_1440_agent()
    query = "How do I change the oil filter?"
    result = agent.run_query(query)  # type: ignore[attr-defined]
    print(result)

