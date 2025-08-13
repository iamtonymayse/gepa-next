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
    def __init__(self, api_key: str, *, extra_headers: Dict[str, str] | None = None, timeout: float = 5.0) -> None:
        self.api_key = api_key
        headers = {
            "User-Agent": "gepa-next/0.1",
            "Authorization": f"Bearer {api_key}",
        }
        if extra_headers:
            headers.update(extra_headers)
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers)
        self._extra_headers = extra_headers or {}

    async def complete(self, prompt: str, **kwargs: object) -> str:
        settings = get_settings()
        try:
            messages = kwargs.get("messages")
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")
            model = kwargs.get("model") or settings.TARGET_DEFAULT_MODEL_ID
            body: Dict[str, object] = {
                "model": model,
                "messages": messages if messages is not None else [{"role": "user", "content": prompt}],
            }
            if temperature is not None:
                body["temperature"] = temperature
            if max_tokens is not None:
                body["max_tokens"] = max_tokens
            resp = await self.client.post("https://openrouter.ai/api/v1/chat/completions", json=body)
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return "unavailable"

    async def aclose(self) -> None:
        with suppress(Exception):
            await self.client.aclose()


class OpenAIProvider:
    def __init__(self, api_key: str, *, timeout: float = 5.0) -> None:
        headers = {
            "User-Agent": "gepa-next/0.1",
            "Authorization": f"Bearer {api_key}",
        }
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers)

    async def complete(self, prompt: str, **kwargs: object) -> str:
        try:
            messages = kwargs.get("messages")
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")
            model = kwargs.get("model")
            body: Dict[str, object] = {
                "model": model,
                "messages": messages if messages is not None else [{"role": "user", "content": prompt}],
            }
            if temperature is not None:
                body["temperature"] = temperature
            if max_tokens is not None:
                body["max_tokens"] = max_tokens
            resp = await self.client.post("https://api.openai.com/v1/chat/completions", json=body)
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return "unavailable"

    async def aclose(self) -> None:
        with suppress(Exception):
            await self.client.aclose()


_target_provider_singleton: ModelProvider | None = None
_judge_provider_singleton: ModelProvider | None = None


def get_target_provider(settings: Optional[Settings] = None) -> ModelProvider:
    settings = settings or get_settings()
    if settings.USE_MODEL_STUB or not settings.OPENROUTER_API_KEY:
        return LocalEchoProvider()
    global _target_provider_singleton
    if (
        not isinstance(_target_provider_singleton, OpenRouterProvider)
        or _target_provider_singleton.api_key != settings.OPENROUTER_API_KEY
    ):
        _target_provider_singleton = OpenRouterProvider(settings.OPENROUTER_API_KEY)
    return _target_provider_singleton


def get_judge_provider(settings: Optional[Settings] = None) -> ModelProvider:
    settings = settings or get_settings()
    if settings.USE_MODEL_STUB:
        return LocalEchoProvider()
    global _judge_provider_singleton
    if settings.JUDGE_PROVIDER == "openrouter" and settings.OPENROUTER_API_KEY:
        extra: Dict[str, str] | None = None
        if settings.OPENAI_API_KEY:
            extra = {"X-OpenAI-Api-Key": settings.OPENAI_API_KEY}
        if (
            not isinstance(_judge_provider_singleton, OpenRouterProvider)
            or _judge_provider_singleton.api_key != settings.OPENROUTER_API_KEY
            or getattr(_judge_provider_singleton, "_extra_headers", {}) != (extra or {})
        ):
            _judge_provider_singleton = OpenRouterProvider(
                settings.OPENROUTER_API_KEY,
                extra_headers=extra,
                timeout=settings.JUDGE_TIMEOUT_S,
            )
        return _judge_provider_singleton
    if settings.JUDGE_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        if (
            not isinstance(_judge_provider_singleton, OpenAIProvider)
            or _judge_provider_singleton.client.headers.get("Authorization")
            != f"Bearer {settings.OPENAI_API_KEY}"
        ):
            _judge_provider_singleton = OpenAIProvider(
                settings.OPENAI_API_KEY, timeout=settings.JUDGE_TIMEOUT_S
            )
        return _judge_provider_singleton
    return LocalEchoProvider()


def get_provider_from_env(settings: Optional[Settings] = None) -> ModelProvider:
    settings = settings or get_settings()
    if settings.USE_MODEL_STUB or not settings.OPENROUTER_API_KEY:
        return LocalEchoProvider()
    return OpenRouterProvider(settings.OPENROUTER_API_KEY)


async def close_all_providers() -> None:
    global _target_provider_singleton, _judge_provider_singleton
    for prov in (_target_provider_singleton, _judge_provider_singleton):
        if isinstance(prov, (OpenRouterProvider, OpenAIProvider)):
            with suppress(Exception):
                await prov.aclose()  # type: ignore[func-returns-value]
    _target_provider_singleton = None
    _judge_provider_singleton = None
