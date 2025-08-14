import importlib
from fastapi.testclient import TestClient


def test_sse_progress_has_delta_and_finished_reason(monkeypatch) -> None:
    # Minimal auth so we don't trip middleware
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)

    with TestClient(main.app) as client:
        r = client.post(
            "/v1/optimize",
            json={"prompt": "hi", "target_model_id": "openai/gpt-5-mini"},
            headers={"Authorization": "Bearer token"},
            params={"iterations": 2},
        )
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        got_delta = False
        finished_seen = False

        with client.stream(
            "GET",
            f"/v1/optimize/{job_id}/events",
            headers={"Authorization": "Bearer token"},
        ) as stream:
            line_iter = stream.iter_lines()
            first = next(line_iter)
            assert first.startswith("retry:")
            for line in line_iter:
                if not line:
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:") :].strip()
                    if '"type":"progress"' in payload and '"delta_best"' in payload:
                        got_delta = True
                    if '"type":"finished"' in payload and '"reason"' in payload:
                        finished_seen = True
                        break

        assert got_delta and finished_seen
