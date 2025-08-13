from __future__ import annotations

import httpx
from contextlib import suppress
from typing import Optional, Protocol, Dict

from ..settings import Settings, get_settings


class ModelProvider(Protocol):
    async def complete(self, prompt: str, **kwargs: object) -> str: ...


class LocalEchoProvider:
    async def complete(self, prompt: str, **kwargs: object) -> str:
        text = " ".join(prompt.strip().split())
        return text[:50]


class OpenRouterProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=5.0,
            headers={
                "User-Agent": "gepa-next/0.1",
                "Authorization": f"Bearer {api_key}",
            },
        )

    async def complete(self, prompt: str, **kwargs: object) -> str:
        settings = get_settings()
        try:
            messages = kwargs.get("messages")
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")
            body: Dict[str, object] = {
                "model": settings.MODEL_ID,
                "messages": messages
                if messages is not None
                else [{"role": "user", "content": prompt}],
            }
            if temperature is not None:
                body["temperature"] = temperature
            if max_tokens is not None:
                body["max_tokens"] = max_tokens
            resp = await self.client.post(
                "https://openrouter.ai/api/v1/chat/completions", json=body
            )
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return "unavailable"

    async def aclose(self) -> None:
        with suppress(Exception):
            await self.client.aclose()


_provider_singleton: OpenRouterProvider | None = None


def get_provider_from_env(settings: Optional[Settings] = None) -> ModelProvider:
    settings = settings or get_settings()
    if not settings.USE_MODEL_STUB and settings.OPENROUTER_API_KEY:
        global _provider_singleton
        if (
            _provider_singleton is None
            or _provider_singleton.api_key != settings.OPENROUTER_API_KEY
        ):
            _provider_singleton = OpenRouterProvider(settings.OPENROUTER_API_KEY)
        return _provider_singleton
    return LocalEchoProvider()


async def close_provider() -> None:
    global _provider_singleton
    if isinstance(_provider_singleton, OpenRouterProvider):
        await _provider_singleton.aclose()
    _provider_singleton = None
