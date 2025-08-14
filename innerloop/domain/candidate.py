from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any, List, Mapping, Sequence


@dataclass
class Candidate:
    id: str
    sections: List[str]
    examples_subset: List[int] | None = None
    meta: dict = field(default_factory=dict)


def apply_edits(candidate: Candidate, edits: Sequence[Mapping[str, Any]]) -> Candidate:
    from .operators import OPERATORS

    new = Candidate(
        candidate.id,
        list(candidate.sections),
        list(candidate.examples_subset or []),
        dict(candidate.meta),
    )
    for edit in edits:
        op_name = str(edit.get("op", ""))
        if not op_name:
            continue
        args = edit.get("args", {})
        seed = int(edit.get("seed", 0))
        op = OPERATORS.get(op_name)
        if not op:
            continue
        rng = random.Random(seed)  # nosec B311
        new = op(new, rng=rng, **args)
    return new
