import importlib
import json

from fastapi.testclient import TestClient
import pytest


def create_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return TestClient(main.app)


@pytest.mark.timeout(5)
def test_optimize_examples_objectives(monkeypatch):
    client = create_client(monkeypatch)
    body = {
        "prompt": "hello",
        "examples": [{"input": "foo"}, {"input": "bar", "expected": "baz"}],
        "objectives": ["brevity", "diversity", "coverage"],
        "seed": 123,
    }
    with client:
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
            progress_seen = False
            finished_scores = None
            for line in line_iter:
                if line.startswith("data:"):
                    env = json.loads(line.split(":", 1)[1])
                    if env["type"] == "progress" and "scores" in env["data"]:
                        progress_seen = True
                    if env["type"] == "finished":
                        finished_scores = env["data"].get("scores")
                        break
            assert progress_seen
            assert finished_scores is not None
            assert all(
                k in finished_scores for k in ["brevity", "diversity", "coverage"]
            )
        # determinism with seed
        resp1 = client.post(
            "/v1/optimize", json={**body, "seed": 123}, params={"iterations": 1}
        )
        resp2 = client.post(
            "/v1/optimize", json={**body, "seed": 123}, params={"iterations": 1}
        )
        job1 = resp1.json()["job_id"]
        job2 = resp2.json()["job_id"]
        props = []
        for job in (job1, job2):
            with client.stream(
                "GET",
                f"/v1/optimize/{job}/events",
                headers={"Authorization": "Bearer token"},
            ) as stream:
                line_iter = stream.iter_lines()
                next(line_iter)
                for line in line_iter:
                    if line.startswith("data:"):
                        env = json.loads(line.split(":", 1)[1])
                        if env["type"] == "finished":
                            props.append(env["data"]["proposal"])
                            break
        assert props[0] == props[1]
