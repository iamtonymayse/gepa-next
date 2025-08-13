from __future__ import annotations

import importlib
import logging

from fastapi.testclient import TestClient


def test_authorization_header_redacted(monkeypatch, caplog):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings  # type: ignore

    importlib.reload(settings)
    import innerloop.main as main  # type: ignore

    importlib.reload(main)
    logger = logging.getLogger("gepa")
    with caplog.at_level(logging.INFO, logger="gepa"):
        with TestClient(main.app) as client:
            client.post(
                "/v1/optimize",
                json={"prompt": "hi"},
                headers={"Authorization": "Bearer token"},
            )

    # Find our structured "request" log and assert redaction
    records = [r for r in caplog.records if r.getMessage() == "request"]
    assert records, "expected a 'request' log record"
    redacted_seen = False
    for rec in records:
        headers = getattr(rec, "headers", {})
        if headers:
            val = headers.get("Authorization") or headers.get("authorization")
            if val is not None:
                assert val == "REDACTED"
                redacted_seen = True
    assert redacted_seen, "no Authorization header captured on record"

