from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import List

from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given
from hypothesis import settings as hsettings
from hypothesis import strategies as st

from innerloop.api.sse import SSE_TERMINALS as TERMINALS
from innerloop.domain.optimize_engine import pareto_filter


def _dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


@hsettings(max_examples=100, deadline=None)
@given(
    st.lists(st.text(min_size=0, max_size=8), min_size=0, max_size=12),
    st.integers(min_value=1, max_value=5),
)
def test_pareto_invariants(items: List[str], n: int) -> None:
    # Determinism & size bound
    r1 = pareto_filter(items, n=n)
    r2 = pareto_filter(items, n=n)
    assert r1 == r2
    assert len(r1) <= min(n, len(items))
    # Subset of inputs
    for x in r1:
        assert x in items

    # No member strictly dominated by another member under default objectives
    def score(s: str) -> tuple[int, int]:
        return (len(s), -len(set(s.lower().split())))

    scored = [(x, score(x)) for x in r1]
    for i, (_, si) in enumerate(scored):
        for j, (_, sj) in enumerate(scored):
            if i != j:
                assert not _dominates(sj, si)


@hsettings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.integers(min_value=1, max_value=3))
def test_sse_invariants(monkeypatch, iterations: int) -> None:
    # auth bypass for /optimize
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings  # type: ignore

    importlib.reload(settings)
    import innerloop.main as main  # type: ignore

    importlib.reload(main)
    with TestClient(main.app) as client:
        headers = {"Authorization": "Bearer token"}
        job_id = client.post(
            "/v1/optimize",
            json={"prompt": "x"},
            params={"iterations": iterations},
            headers=headers,
        ).json()["job_id"]

        with client.stream(
            "GET", f"/v1/optimize/{job_id}/events", headers=headers
        ) as stream:
            it = stream.iter_lines()
            first = next(it)
            assert first.startswith("retry:")
            ids: list[int] = []
            events: list[str] = []
            for line in it:
                if line.startswith("id:"):
                    try:
                        ids.append(int(line.split(":", 1)[1]))
                    except Exception:
                        pass
                elif line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                elif line.startswith("data:") and events and events[-1] in TERMINALS:
                    break

            assert ids == sorted(ids), "event ids must be monotonically increasing"
            assert events[0] == "started"
            terminals = [e for e in events if e in TERMINALS]
            assert len(terminals) == 1, f"expected exactly 1 terminal, saw {terminals}"


def test_sse_golden_sequence(monkeypatch) -> None:
    """Golden SSE sequence for iterations=1."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings  # type: ignore

    importlib.reload(settings)
    import innerloop.main as main  # type: ignore

    importlib.reload(main)
    with TestClient(main.app) as client:
        headers = {"Authorization": "Bearer token"}
        job_id = client.post(
            "/v1/optimize",
            json={"prompt": "hi"},
            params={"iterations": 1},
            headers=headers,
        ).json()["job_id"]

        with client.stream(
            "GET", f"/v1/optimize/{job_id}/events", headers=headers
        ) as stream:
            it = stream.iter_lines()
            next(it)  # retry prelude
            seen: list[str] = []
            for line in it:
                if line.startswith("event:"):
                    ev = line.split(":", 1)[1].strip()
                    if ev in {"started", "progress", "finished"}:
                        seen.append(ev)
                elif line.startswith("data:") and seen and seen[-1] in TERMINALS:
                    break

    snap = Path("tests/snapshots/sse_events.snap.json")
    expect = json.loads(snap.read_text(encoding="utf-8"))
    assert seen == expect
