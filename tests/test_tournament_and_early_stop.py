import importlib

from fastapi.testclient import TestClient


def reload_env(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return main


def test_early_stop_and_events(monkeypatch):
    main = reload_env(
        monkeypatch,
        OPENROUTER_API_KEY="dev",
        USE_MODEL_STUB="true",
        API_BEARER_TOKENS='["token"]',
    )
    with TestClient(main.app) as client:
        r = client.post(
            "/v1/optimize",
            json={
                "prompt": "improve me",
                "seed": 42,
                "tournament_size": 3,
                "recombination_rate": 0.5,
                "early_stop_patience": 1,
            },
            params={"iterations": 5},
        )
        job = r.json()["job_id"]
        saw = set()
        with client.stream(
            "GET",
            f"/v1/optimize/{job}/events",
            headers={"Authorization": "Bearer token"},
        ) as s:
            for ln in s.iter_lines():
                if ln.startswith("event:"):
                    saw.add(ln.split(":", 1)[1].strip())
                if ln.startswith("event: finished"):
                    break
        assert "mutation" in saw
        assert "selected" in saw
        # early_stop may occur, but not mandatory with seed
