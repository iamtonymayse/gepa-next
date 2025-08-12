import importlib
import time

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
    return TestClient(main.app), settings


def test_sse_headers(monkeypatch):
    client, _ = create_client(monkeypatch, OPENROUTER_API_KEY="dev")
    with client:
        resp = client.post("/optimize", params={"iterations": 1})
        job_id = resp.json()["job_id"]
        resp = client.get(f"/optimize/{job_id}/events")
        assert resp.headers["cache-control"] == "no-store"
        assert resp.headers["connection"] == "keep-alive"
        assert resp.headers["x-accel-buffering"] == "no"


def test_auth_matrix(monkeypatch):
    # No auth -> 401
    client, _ = create_client(monkeypatch, API_BEARER_TOKENS='["token1"]', OPENROUTER_API_KEY=None)
    with client:
        resp = client.post("/optimize")
        assert resp.status_code == 401
    # Bearer token -> 200
    client, _ = create_client(monkeypatch, API_BEARER_TOKENS='["token1"]', OPENROUTER_API_KEY=None)
    with client:
        resp = client.post("/optimize", headers={"Authorization": "Bearer token1"})
        assert resp.status_code == 200
    # Bypass via OPENROUTER_API_KEY
    client, _ = create_client(monkeypatch, OPENROUTER_API_KEY="dev", API_BEARER_TOKENS=None)
    with client:
        resp = client.post("/optimize")
        assert resp.status_code == 200


def test_iterations_clamp(monkeypatch):
    client, settings_module = create_client(monkeypatch, OPENROUTER_API_KEY="dev")
    with client:
        resp = client.post("/optimize", params={"iterations": 9999})
        job_id = resp.json()["job_id"]
        with client.stream("GET", f"/optimize/{job_id}/events") as stream:
            line_iter = stream.iter_lines()
            progress = 0
            start = time.time()
            for line in line_iter:
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    if event == "progress":
                        progress += 1
                    if event == "finished":
                        break
                if time.time() - start > 5:
                    break
        assert progress >= 1
        assert progress <= settings_module.get_settings().MAX_ITERATIONS


def test_request_size_limit(monkeypatch):
    client, _ = create_client(monkeypatch, OPENROUTER_API_KEY="dev", MAX_REQUEST_BYTES=10)
    with client:
        resp = client.post("/optimize", json={"data": "x" * 50})
        assert resp.status_code == 413


def test_rate_limit(monkeypatch):
    client, _ = create_client(
        monkeypatch,
        OPENROUTER_API_KEY="dev",
        RATE_LIMIT_OPTIMIZE_RPS=1,
        RATE_LIMIT_OPTIMIZE_BURST=2,
    )
    with client:
        statuses = [client.post("/optimize").status_code for _ in range(10)]
        assert any(code == 429 for code in statuses)


def test_request_id_header(monkeypatch):
    client, _ = create_client(monkeypatch, OPENROUTER_API_KEY="dev")
    with client:
        resp = client.get("/healthz")
        assert "x-request-id" in resp.headers
        resp2 = client.get("/healthz", headers={"X-Request-ID": "abc"})
        assert resp2.headers["x-request-id"] == "abc"
