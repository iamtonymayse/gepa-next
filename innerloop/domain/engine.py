from __future__ import annotations

from typing import Protocol

from ..settings import get_settings


class ModelProvider(Protocol):
    async def complete(self, prompt: str, **kwargs: object) -> str: ...


class LocalEchoProvider:
    async def complete(self, prompt: str, **kwargs: object) -> str:
        return f"echo:{prompt[::-1][:20]}"


def get_provider_from_env() -> ModelProvider:
    _ = get_settings().OPENROUTER_API_KEY
    return LocalEchoProvider()
