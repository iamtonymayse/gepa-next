from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass
class Candidate:
    id: str
    sections: List[str]
    examples_subset: Sequence[int] | None = None
    meta: dict = field(default_factory=dict)


def apply_edits(candidate: Candidate, edits: Sequence[dict]) -> Candidate:
    from .operators import OPERATORS

    new = Candidate(
        candidate.id,
        list(candidate.sections),
        list(candidate.examples_subset or []),
        dict(candidate.meta),
    )
    for edit in edits:
        op_name = edit.get("op")
        args = edit.get("args", {})
        seed = edit.get("seed", 0)
        op = OPERATORS.get(op_name)
        if not op:
            continue
        rng = random.Random(seed)
        new = op(new, rng=rng, **args)
    return new
