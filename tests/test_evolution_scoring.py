from innerloop.evolution.scoring import (
    brevity_score,
    clamp,
    composite_score,
    normalize_judge,
)


def test_normalize_and_composite_bounds() -> None:
    j = {"brevity": 10.0, "diversity": 8.0, "coverage": 7.0}
    jn = normalize_judge(j)
    assert all(0.0 <= v <= 1.0 for v in jn.values())
    # clamp should bound values to [0,1]
    assert clamp(-0.5) == 0.0 and clamp(1.5) == 1.0
    b = brevity_score("x" * 400, target_chars=600)
    assert 0.0 <= b <= 1.0
    score = composite_score(
        jn,
        coverage=jn.get("coverage", 0.0),
        diversity=jn.get("diversity", 0.0),
        brevity=b,
    )
    assert 0.0 <= score <= 1.0
