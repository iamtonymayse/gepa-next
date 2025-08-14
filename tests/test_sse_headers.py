import importlib
import re

from fastapi.testclient import TestClient


def _mkapp(monkeypatch):
    """Create app with minimal auth to avoid middleware rejection."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return main.app


def test_sse_headers_and_prelude(monkeypatch):
    app = _mkapp(monkeypatch)
    client = TestClient(app)
    with client:
        resp = client.post(
            "/v1/optimize",
            json={"prompt": "hi"},
            headers={"Authorization": "Bearer token"},
            params={"iterations": 1},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            headers = {k.lower(): v for k, v in stream.headers.items()}
            assert headers.get("content-type", "").startswith("text/event-stream")
            assert headers.get("x-accel-buffering") == "no"
            assert "cache-control" in headers and re.search(
                r"no-(cache|store)", headers["cache-control"]
            )
            first = next(stream.iter_lines())
            assert first.startswith("retry:")
