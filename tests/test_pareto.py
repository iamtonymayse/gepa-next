from innerloop.domain.optimize_engine import pareto_filter


def test_pareto_front_deterministic():
    proposals = [
        "alpha beta gamma",
        "alpha beta",
        "gamma",
        "a b c d e",
    ]
    front = pareto_filter(proposals, n=2)
    assert front == ["gamma", "a b c d e"]
