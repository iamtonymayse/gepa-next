from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, Literal, Optional

import httpx
from pydantic import BaseModel

TERMINALS = {"finished", "failed", "cancelled", "shutdown"}


class JobState(BaseModel):
    job_id: str
    status: str
    created_at: float
    updated_at: float
    result: Dict[str, Any] | None = None


class SSEEnvelope(BaseModel):
    type: Literal["started", "progress", "finished", "failed", "cancelled", "shutdown"]
    schema_version: int = 1
    job_id: str
    ts: float
    id: int | None = None
    data: Dict[str, Any]


class GepaClient:
    def __init__(
        self,
        base_url: str,
        bearer_token: str | None = None,
        openrouter_key: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.openrouter_key = openrouter_key
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._last_ids: Dict[str, int] = {}

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GepaClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if extra:
            headers.update(extra)
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.openrouter_key:
            headers["OpenRouter-API-Key"] = self.openrouter_key
        return headers

    async def create_job(
        self,
        prompt: str,
        context: Dict[str, Any] | None = None,
        iterations: int | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        headers = self._headers(
            {"Idempotency-Key": idempotency_key} if idempotency_key else None
        )
        params = {"iterations": iterations} if iterations is not None else None
        payload: Dict[str, Any] = {"prompt": prompt}
        if context is not None:
            payload["context"] = context
        resp = await self._client.post(
            "/v1/optimize", json=payload, params=params, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return data["job_id"]

    async def state(self, job_id: str) -> JobState:
        resp = await self._client.get(
            f"/v1/optimize/{job_id}", headers=self._headers()
        )
        resp.raise_for_status()
        return JobState(**resp.json())

    async def cancel(self, job_id: str) -> None:
        resp = await self._client.delete(
            f"/v1/optimize/{job_id}", headers=self._headers()
        )
        resp.raise_for_status()

    async def stream(
        self, job_id: str, last_event_id: int | None = None
    ) -> AsyncIterator[SSEEnvelope]:
        backoff = 0.1
        last_id = last_event_id or self._last_ids.get(job_id, 0)
        headers = self._headers(
            {"Last-Event-ID": str(last_id)} if last_id else None
        )
        while True:
            try:
                async with self._client.stream(
                    "GET",
                    f"/v1/optimize/{job_id}/events",
                    headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    event_id: Optional[int] = None
                    data_buf = ""
                    async for line in resp.aiter_lines():
                        if line == "":
                            if data_buf:
                                envelope = json.loads(data_buf)
                                last_id = envelope.get("id", event_id or last_id)
                                self._last_ids[job_id] = last_id
                                yield SSEEnvelope(**envelope)
                                if envelope["type"] in TERMINALS:
                                    return
                            event_id = None
                            data_buf = ""
                        elif line.startswith(":"):
                            continue
                        elif line.startswith("retry:"):
                            continue
                        elif line.startswith("id:"):
                            try:
                                event_id = int(line.split(":", 1)[1])
                            except ValueError:
                                pass
                        elif line.startswith("data:"):
                            data_buf += line.split(":", 1)[1].strip()
                        # ignore event: line; type is in data
            except httpx.HTTPError:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 5)
                headers = self._headers({"Last-Event-ID": str(last_id)})
                continue

    async def resume(self, job_id: str) -> AsyncIterator[SSEEnvelope]:
        last = self._last_ids.get(job_id)
        async for env in self.stream(job_id, last):
            yield env
