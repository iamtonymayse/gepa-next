import importlib

from fastapi.testclient import TestClient


def test_idempotent_job_creation(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    from innerloop.api import metrics

    with TestClient(main.app) as client:
        before = metrics.snapshot()["jobs_created"]
        headers = {"Idempotency-Key": "same"}
        r1 = client.post("/v1/optimize", json={"prompt": "hi"}, headers=headers)
        r2 = client.post("/v1/optimize", json={"prompt": "hi"}, headers=headers)
        assert r1.json()["job_id"] == r2.json()["job_id"]
        assert metrics.snapshot()["jobs_created"] == before + 1
        r3 = client.post(
            "/v1/optimize", json={"prompt": "hi"}, headers={"Idempotency-Key": "other"}
        )
        assert r3.json()["job_id"] != r1.json()["job_id"]
