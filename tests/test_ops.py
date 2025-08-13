import importlib
import json
import time

import pytest
from fastapi.testclient import TestClient


def create_client(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_401_no_bypass(monkeypatch):
    client = create_client(monkeypatch, OPENROUTER_API_KEY=None, API_BEARER_TOKENS=None)
    with client:
        resp = client.post("/optimize", json={"prompt": "hi"}, headers={"X-Request-ID": "test-req"})
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "unauthorized"
        assert resp.headers["x-request-id"] == "test-req"


def test_events_404(monkeypatch):
    client = create_client(
        monkeypatch, OPENROUTER_API_KEY="dev", API_BEARER_TOKENS='["token"]'
    )
    with client:
        resp = client.get(
            "/optimize/does-not-exist/events", headers={"Authorization": "Bearer token"}
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


def test_state_endpoint(monkeypatch):
    client = create_client(
        monkeypatch, OPENROUTER_API_KEY="dev", API_BEARER_TOKENS='["token"]'
    )
    with client:
        job_id = client.post("/optimize", json={"prompt": "hi"}).json()["job_id"]
        state = client.get(
            f"/optimize/{job_id}", headers={"Authorization": "Bearer token"}
        ).json()
        assert state["status"] in {"running", "finished"}


def test_cancel_flow(monkeypatch):
    client = create_client(
        monkeypatch, OPENROUTER_API_KEY="dev", API_BEARER_TOKENS='["token"]'
    )
    with client:
        job_id = client.post(
            "/optimize", json={"prompt": "hi"}, params={"iterations": 2}
        ).json()["job_id"]
        client.delete(
            f"/optimize/{job_id}", headers={"Authorization": "Bearer token"}
        )
        deadline = time.time() + 1
        while time.time() < deadline:
            state = client.get(
                f"/optimize/{job_id}", headers={"Authorization": "Bearer token"}
            ).json()
            if state["status"] == "cancelled":
                break
            time.sleep(0.05)
        else:
            pytest.fail("not cancelled")
        with client.stream(
            "GET", f"/optimize/{job_id}/events", headers={"Authorization": "Bearer token"}
        ) as stream:
            events = [line for line in stream.iter_lines() if line.startswith("event:")]
        assert any(e == "event: cancelled" for e in events)
        resp = client.delete(
            f"/optimize/{job_id}", headers={"Authorization": "Bearer token"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "not_cancelable"


def test_rate_limit(monkeypatch):
    client = create_client(
        monkeypatch, OPENROUTER_API_KEY="dev", RATE_LIMIT_OPTIMIZE_RPS=1, RATE_LIMIT_OPTIMIZE_BURST=1
    )
    with client:
        codes = []
        bodies = []
        for _ in range(3):
            resp = client.post("/optimize", json={"prompt": "hi"})
            codes.append(resp.status_code)
            if resp.status_code == 429:
                bodies.append(resp.json())
        assert any(c == 429 for c in codes)
        for body in bodies:
            assert body["error"]["code"] == "rate_limited"


def test_size_limit(monkeypatch):
    client = create_client(monkeypatch, OPENROUTER_API_KEY="dev", MAX_REQUEST_BYTES=10)
    with client:
        resp = client.post("/optimize", json={"prompt": "x" * 50})
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "payload_too_large"


def test_sse_schema(monkeypatch):
    client = create_client(
        monkeypatch, OPENROUTER_API_KEY="dev", API_BEARER_TOKENS='["token"]'
    )
    with client:
        job_id = client.post("/optimize", json={"prompt": "hi"}).json()["job_id"]
        with client.stream(
            "GET", f"/optimize/{job_id}/events", headers={"Authorization": "Bearer token"}
        ) as stream:
            it = stream.iter_lines()
            prelude = next(it)
            assert prelude.startswith("retry:")
            event = None
            data = None
            for line in it:
                if line.startswith("event:"):
                    event = line
                if line.startswith("data:"):
                    data = line
                    break
            assert event is not None and data is not None
            payload = json.loads(data.split(":", 1)[1])
            for key in ["type", "schema_version", "job_id", "ts", "data"]:
                assert key in payload

