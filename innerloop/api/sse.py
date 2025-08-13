from __future__ import annotations

import json
from typing import Dict

SSE_TERMINALS = {"finished", "failed", "cancelled", "shutdown"}


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
    return (
        id_line
        + f"event: {event_type}\n"
        + f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )


def prelude_retry_ms(ms: int) -> bytes:
    return f"retry: {ms}\n\n".encode()

