from __future__ import annotations

from typing import Dict, Tuple


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *x* into the inclusive range [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def normalize_judge(judge: Dict[str, float], scale: float = 10.0) -> Dict[str, float]:
    """Normalize raw judge subscores (typically 0..10) to 0..1 and clamp.

    Non-numeric values are skipped. Unknown keys pass through unchanged
    after normalization attempt.
    """
    out: Dict[str, float] = {}
    for k, v in judge.items():
        try:
            out[k] = clamp(float(v) / scale)
        except Exception:
            # if value is non-numeric, drop it
            continue
    return out


def brevity_score(text: str, target_chars: int = 600) -> float:
    """Brevity score in [0,1].

    Returns 1.0 if ``text`` length is at or below ``target_chars``. The
    score then decays linearly to 0.0 at 3 * ``target_chars`` and is never
    negative.
    """
    n = len(text or "")
    if n <= target_chars:
        return 1.0
    span = 2 * target_chars
    rem = max(0.0, 1.0 - (n - target_chars) / float(span))
    return clamp(rem)


def composite_score(
    judge_norm: Dict[str, float],
    coverage: float,
    diversity: float,
    brevity: float,
    weights: Tuple[float, float, float, float] = (0.6, 0.1, 0.2, 0.1),
) -> float:
    """Compute a single composite score in [0,1] from normalized components."""
    wj, wc, wd, wb = weights
    j_vals = list(judge_norm.values())
    j_mean = sum(j_vals) / len(j_vals) if j_vals else 0.0
    score = (
        wj * clamp(j_mean)
        + wc * clamp(coverage)
        + wd * clamp(diversity)
        + wb * clamp(brevity)
    )
    return clamp(score)
