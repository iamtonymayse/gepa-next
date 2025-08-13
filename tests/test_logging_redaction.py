import importlib
import logging
from fastapi.testclient import TestClient


class _StubLogger:
    def __init__(self) -> None:
        self.last_extra = None

    def info(self, msg, *, extra=None):
        self.last_extra = extra


def test_logging_redacts_secret_headers(monkeypatch):
    stub = _StubLogger()

    real_getlogger = logging.getLogger

    def fake_getlogger(name=None):
        if name == "gepa":
            return stub
        return real_getlogger(name)

    monkeypatch.setattr(logging, "getLogger", fake_getlogger)
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)

    with TestClient(main.app) as client:
        client.get(
            "/v1/healthz",
            headers={
                "Authorization": "Bearer secret",
                "OpenRouter-API-Key": "super-secret",
                "X-OpenAI-API-Key": "another-secret",
            },
        )

    hdrs = {k.lower(): v for k, v in stub.last_extra.get("headers", {}).items()}
    assert hdrs.get("authorization") == "REDACTED"
    assert hdrs.get("openrouter-api-key") == "REDACTED"
    assert hdrs.get("x-openai-api-key") == "REDACTED"

