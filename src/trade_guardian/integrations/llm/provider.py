from __future__ import annotations


class LLMProvider:
    """Placeholder LLM provider integration."""

    def __init__(self, model_name: str = "stub-model") -> None:
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        return f"[{self.model_name}] Echo: {prompt}"


