from types import SimpleNamespace

from innerloop.domain import gepa_loop


def test_diversity_meta_and_selection(monkeypatch):
    def fake_pareto(items, objectives=None, n=None):
        return list(items)

    monkeypatch.setattr(gepa_loop, "pareto_filter", fake_pareto)

    cand_a = SimpleNamespace(id="A", sections=["solve by step one two three"], meta={"judge_score": 1.0})
    cand_b = SimpleNamespace(id="B", sections=["solve by step one two three"], meta={"judge_score": 1.0})
    cand_c = SimpleNamespace(id="C", sections=["completely different answer path"], meta={"judge_score": 1.0})
    scored = [cand_a, cand_b, cand_c]

    texts = ["\n".join(c.sections) for c in scored]
    for i, c in enumerate(scored):
        max_j = gepa_loop._max_jaccard_3gram(texts[i], texts[:i] + texts[i + 1 :])
        c.meta["diversity"] = 1.0 - max_j

    frontier = gepa_loop.pareto_filter(scored, objectives=None, n=len(scored))
    frontier.sort(
        key=lambda c: (
            c.meta.get("judge_score", 0.0),
            c.meta.get("diversity", 0.0),
        ),
        reverse=True,
    )
    assert frontier[0].id == "C"
