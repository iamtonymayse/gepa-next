from __future__ import annotations

from typing import Dict

try:
    import orjson  # type: ignore

    def json_dumps(obj: Dict) -> str:
        return orjson.dumps(obj).decode("utf-8")

except Exception:  # pragma: no cover
    import json

    def json_dumps(obj: Dict) -> str:
        return json.dumps(obj, separators=(",", ":"))


# Terminal event names used across routers and clients.
# Keep this list stable; tests rely on it.
SSE_TERMINALS = {"finished", "failed", "cancelled"}


def format_sse(event_type: str, envelope: Dict) -> str:
    payload = {
        "type": event_type,
        "schema_version": 1,
        "job_id": envelope.get("job_id"),
        "ts": envelope.get("ts"),
        "id": envelope.get("id"),
        "data": envelope.get("data", {}),
    }
    id_line = f"id: {envelope['id']}\n" if envelope.get("id") is not None else ""
    return id_line + f"event: {event_type}\n" + f"data: {json_dumps(payload)}\n\n"


def prelude_retry_ms(ms: int) -> bytes:
    return f"retry: {ms}\n\n".encode()
