import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .config import Settings


@dataclass
class LlmResult:
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class LlmProvider(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmResult: ...


class HttpLlmProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.llm_base_url.rstrip("/")

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmResult:
        if not self.settings.llm_api_key or not self.base_url or not self.settings.llm_model:
            raise RuntimeError("LLM provider is not configured")
        payload = {"model": self.settings.llm_model, "messages": messages, "tools": tools}
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        return LlmResult(text=message.get("content") or "", tool_calls=message.get("tool_calls") or [])


class MockLlmProvider:
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LlmResult:
        if any(message.get("role") == "tool" for message in messages):
            return LlmResult()
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        normalized = " ".join(user_text.casefold().split())
        if normalized in {"привет", "здравствуйте", "добрый день", "hello", "hi"}:
            return LlmResult(text="Здравствуйте! Напишите название, артикул или характеристики товара.")

        query = re.sub(
            r"^(?:пожалуйста[,.]?\s*)?(?:найди(?:те)?|покажи(?:те)?|ищу|нуж(?:ен|на|ны|но)|хочу купить)\s+",
            "",
            user_text.strip(),
            flags=re.IGNORECASE,
        ).strip(" .,!?:;")
        query = query or user_text.strip()
        return LlmResult(
            tool_calls=[
                {
                    "function": {
                        "name": "search_products",
                        "arguments": json.dumps(
                            {"query": query, "limit": 5}, ensure_ascii=False
                        ),
                    }
                }
            ]
        )


def build_provider(settings: Settings) -> LlmProvider:
    if settings.llm_provider in {"openai", "deepseek"}:
        return HttpLlmProvider(settings)
    if settings.llm_provider == "mock":
        return MockLlmProvider()
    raise ValueError("LLM_PROVIDER must be openai, deepseek, or mock")
