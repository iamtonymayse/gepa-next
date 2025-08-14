import importlib
import json

from fastapi.testclient import TestClient


def test_target_model_roundtrip(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.post(
            "/v1/optimize?iterations=1",
            json={"prompt": "hello", "target_model": "unit-test-model"},
        )
        job_id = r.json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            it = stream.iter_lines()
            next(it)  # retry:
            saw_target = False
            for line in it:
                if line.startswith("data:"):
                    payload = json.loads(line.split(":", 1)[1])
                    if payload["type"] == "progress":
                        assert (
                            payload["data"]["target_model"] == "unit-test-model"
                        )  # nosec B101
                        saw_target = True
                if line.startswith("event: finished"):
                    break
            assert saw_target  # nosec B101
        state = client.get(
            f"/v1/optimize/{job_id}",
            headers={"Authorization": "Bearer token"},
        ).json()
        assert state["result"]["target_model"] == "unit-test-model"  # nosec B101


def test_target_model_default(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("TARGET_MODEL_DEFAULT", "default-model")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        job_id = client.post("/v1/optimize", json={"prompt": "hello"}).json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as s:
            for line in s.iter_lines():
                if line.startswith("event: finished"):
                    break
        state = client.get(
            f"/v1/optimize/{job_id}",
            headers={"Authorization": "Bearer token"},
        ).json()
        assert state["result"]["target_model"] == "default-model"  # nosec B101
