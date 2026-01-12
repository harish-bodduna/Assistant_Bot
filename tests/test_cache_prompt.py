from optimization.dspy_rag import cache_friendly_prompt


def test_cache_prompt_prefix():
    prompt = cache_friendly_prompt("CTX", "QUESTION")
    assert prompt.startswith("CONTEXT")
    assert "CTX" in prompt
    assert "QUESTION" in prompt

