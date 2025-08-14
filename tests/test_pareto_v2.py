import asyncio
import importlib
import json

from fastapi.testclient import TestClient
import pytest


def test_judge_based_selection(monkeypatch):
    monkeypatch.setenv("USE_JUDGE_STUB", "true")
    monkeypatch.setenv("ENABLE_PARETO_V2", "true")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.domain.optimize_engine as oe

    importlib.reload(oe)
    proposals = ["longer proposal here", "short"]
    best = asyncio.run(
        oe.pareto_v2(prompt="choose", proposals=proposals, n=1, rubric="brevity")
    )
    assert best == ["short"]


@pytest.mark.timeout(5)
def test_rubric_and_target_propagation_in_stream(monkeypatch):
    monkeypatch.setenv("USE_JUDGE_STUB", "true")
    monkeypatch.setenv("ENABLE_PARETO_V2", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.api.models as api_models

    importlib.reload(api_models)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.post(
            "/v1/optimize?iterations=1",
            json={"prompt": "p", "target_model": "m", "evaluation_rubric": "r"},
        )
        job_id = r.json()["job_id"]
        saw = {"rubric": False, "target": False}
        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as s:
            it = s.iter_lines()
            next(it)
            for line in it:
                if line.startswith("data:"):
                    payload = json.loads(line.split(":", 1)[1])
                    if payload["type"] == "progress":
                        data = payload["data"]
                        if data.get("rubric") == "r":
                            saw["rubric"] = True
                        if data.get("target_model") == "m":
                            saw["target"] = True
                if line.startswith("event: finished"):
                    break
        assert all(saw.values())
