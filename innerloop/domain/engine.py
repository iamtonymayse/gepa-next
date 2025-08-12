from __future__ import annotations

import httpx
from typing import Optional, Protocol

from ..settings import get_settings


class ModelProvider(Protocol):
    async def complete(self, prompt: str, **kwargs: object) -> str: ...


class LocalEchoProvider:
    async def complete(self, prompt: str, **kwargs: object) -> str:
        text = " ".join(prompt.strip().split())
        return text[:50]


class OpenRouterProvider:
    def __init__(self, api_key: str) -> None:
        self.client = httpx.AsyncClient(
            timeout=5.0,
            headers={
                "User-Agent": "gepa-next/0.1",
                "Authorization": f"Bearer {api_key}",
            },
        )

    async def complete(self, prompt: str, **kwargs: object) -> str:
        try:
            resp = await self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return "unavailable"


def get_provider_from_env(settings: Optional[object] = None) -> ModelProvider:
    settings = settings or get_settings()
    if not settings.USE_MODEL_STUB and settings.OPENROUTER_API_KEY:
        return OpenRouterProvider(settings.OPENROUTER_API_KEY)
    return LocalEchoProvider()
