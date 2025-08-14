import importlib
import json

from fastapi.testclient import TestClient
import pytest


@pytest.mark.timeout(5)
def test_judge_stub_and_target(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    monkeypatch.setenv("JUDGE_MODEL_ID", "openai:gpt-5-judge")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    body = {
        "prompt": "say hi",
        "examples": [
            {"input": "a", "expected": "A"},
            {"input": "b", "expected": "B"},
        ],
        "objectives": ["brevity", "diversity", "coverage"],
        "target_model_id": "gpt-4o-mini",
        "seed": 123,
    }
    with TestClient(main.app) as client:
        resp = client.post("/v1/optimize", json=body, params={"iterations": 2})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            line_iter = stream.iter_lines()
            first = next(line_iter)
            assert first.startswith("retry:")
            finished = None
            for line in line_iter:
                if line.startswith("data:"):
                    env = json.loads(line[5:])
                    if env["type"] == "progress":
                        assert env["data"]["proposal"]
                        assert "judge" in env["data"]["scores"]
                        assert isinstance(env["data"]["scores"]["judge"], dict)
                    if env["type"] == "finished":
                        finished = env
                        break
            assert finished is not None
            assert "judge" in finished["data"]["scores"]
            proposal1 = finished["data"]["proposal"]
        resp2 = client.post("/v1/optimize", json=body, params={"iterations": 2})
        job2 = resp2.json()["job_id"]
        with client.stream(
            "GET",
            f"/v1/optimize/{job2}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    env = json.loads(line[5:])
                    if env["type"] == "finished":
                        proposal2 = env["data"]["proposal"]
                        break
        assert proposal1 == proposal2
