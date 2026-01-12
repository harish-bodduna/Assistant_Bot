from __future__ import annotations

from typing import Dict, Any

from pydantic import BaseModel
from pydantic_ai import Agent

from retrieval import hybrid_search


class DiagnosticResponse(BaseModel):
    markdown: str


def build_agent() -> Agent[DiagnosticResponse]:
    system_prompt = (
        "You are a technical guide. You will be provided with a Markdown representation of a manual and associated "
        "images. Use the provided Markdown to generate a response. Ensure you keep the text and image references "
        "interleaved exactly as shown in the source. Use Markdown syntax for the final response: Step text...\n\n"
        "![Image Description](image_id)."
    )

    agent = Agent(
        model="gpt-5.2-flagship",
        system_prompt=system_prompt,
        output_type=DiagnosticResponse,
    )

    @agent.tool
    def retrieve_context(user_query: str) -> Dict[str, Any]:
        """Hybrid retrieval with markdown + images."""
        return hybrid_search(user_query)

    return agent


if __name__ == "__main__":
    ag = build_agent()
    result = ag.run("How to reset hydraulic pump?")  # type: ignore[arg-type]
    print(result)

