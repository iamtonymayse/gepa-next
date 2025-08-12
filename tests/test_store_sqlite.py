import importlib
import time

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("store", ["memory", "sqlite"])
def test_persistence_across_reload(monkeypatch, tmp_path, store):
    monkeypatch.setenv("JOB_STORE", store)
    db_path = tmp_path / "gepa.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        headers = {"Idempotency-Key": "abc"}
        job_id = client.post("/v1/optimize", params={"iterations": 1}, headers=headers).json()["job_id"]
        # wait for finish
        deadline = time.time() + 2
        while time.time() < deadline:
            state = client.get(f"/v1/optimize/{job_id}").json()
            if state["status"] == "finished":
                break
            time.sleep(0.05)

    importlib.reload(settings)
    importlib.reload(main)
    with TestClient(main.app) as client2:
        if store == "sqlite":
            with client2.stream("GET", f"/v1/optimize/{job_id}/events") as stream:
                lines = stream.iter_lines()
                next(lines)
                events = []
                for line in lines:
                    if line.startswith("event:"):
                        events.append(line.split(":", 1)[1].strip())
                    if line.startswith("data:") and events and events[-1] == "finished":
                        break
            assert events == ["started", "progress", "finished"]
            resp2 = client2.post("/v1/optimize", headers=headers)
            assert resp2.json()["job_id"] == job_id
        else:
            resp = client2.get(f"/v1/optimize/{job_id}/events")
            assert resp.status_code == 404
            resp2 = client2.post("/v1/optimize", headers=headers)
            assert resp2.json()["job_id"] != job_id
