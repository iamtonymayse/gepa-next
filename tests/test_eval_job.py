import importlib

from fastapi.testclient import TestClient


def app_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_eval_flow(monkeypatch):
    c = app_client(monkeypatch)
    with c:
        c.post(
            "/v1/examples/bulk",
            json=[
                {"input": "great", "expected": "pos"},
                {"input": "bad", "expected": "neg"},
            ],
            headers={"Authorization": "Bearer token"},
        )
        job = c.post(
            "/v1/eval/start",
            json={"name": "baseline", "max_examples": 2, "seed": 7},
            headers={"Authorization": "Bearer token"},
        ).json()["job_id"]
        events = set()
        with c.stream(
            "GET", f"/v1/eval/{job}/events", headers={"Authorization": "Bearer token"}
        ) as s:
            it = s.iter_lines()
            next(it)
            for ln in it:
                if ln.startswith("event:"):
                    ev = ln.split(":", 1)[1].strip()
                    events.add(ev)
                if ln.startswith("event: finished"):
                    break
        assert {"started", "eval_started", "eval_case", "finished"} <= events
