from __future__ import annotations

from typing import List

import dspy
from loguru import logger

from src.config.settings import get_settings


class TroubleshootingSignature(dspy.Signature):
    """
    Instructions: Use the provided Context to answer the User Query.
    The context contains Markdown images in ![alt](url) format.
    You MUST preserve these image links in your response, placing them
    immediately after the instruction they visualize.
    """

    context = dspy.InputField(desc="Structured Markdown from the manual including SAS URLs")
    user_query = dspy.InputField(desc="The technician's specific problem or question")
    interleaved_response = dspy.OutputField(desc="A step-by-step guide with images interleaved")


def configure_lm() -> None:
    """
    Configure DSPy to use GPT-5.2-flagship with project settings.
    """
    settings = get_settings()
    lm = dspy.OpenAI(
        model="gpt-5.2-flagship",
        api_key=settings.openai_api_key,
        api_base=settings.openai_api_base,
    )
    dspy.settings.configure(lm=lm)
    logger.info("DSPy configured with {}", lm.model)


def cache_friendly_prompt(context: str, user_query: str) -> str:
    """
    Prefix retrieved context to maximize prompt caching.
    Context should be llm_markdown (with SAS URLs) from Qdrant.
    """
    return (
        "CONTEXT (pin for caching):\n"
        f"{context}\n\n"
        "TASK: Answer using the context above. Interleave each image exactly where referenced.\n"
        "Do not re-order images. Keep markdown valid and URLs intact.\n"
        f"USER QUERY: {user_query}\n"
        "RESPONSE (interleaved text/images):"
    )


class TroubleshootingProgram(dspy.Module):
    """
    DSPy program using Chain-of-Thought for better structural fidelity.
    """

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(TroubleshootingSignature)

    def forward(self, context: str, user_query: str) -> dspy.Prediction:
        prompt = cache_friendly_prompt(context=context, user_query=user_query)
        return self.predict(context=prompt, user_query=user_query)


def optimize_program(train_examples: List[dspy.Example]) -> TroubleshootingProgram:
    """
    Run BootstrapFewShot over provided examples to get an optimized program.
    """
    configure_lm()
    program = TroubleshootingProgram()
    optimizer = dspy.BootstrapFewShot(metric=lambda gold, pred: 1.0)
    optimized_program = optimizer.compile(program, train_examples)
    logger.info("DSPy program optimized with {} examples", len(train_examples))
    return optimized_program

