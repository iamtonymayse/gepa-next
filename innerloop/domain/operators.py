from __future__ import annotations

import random
from typing import Callable, Dict

from .candidate import Candidate


def edit_constraints(candidate: Candidate, rng: random.Random, note: str | None = None) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    new.meta["constraints"] = note or "edited"
    return new


def reword_objectives(candidate: Candidate, rng: random.Random) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    new.sections = [s + "!" for s in new.sections]
    return new


def reorder_sections(candidate: Candidate, rng: random.Random) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    rng.shuffle(new.sections)
    return new


def toggle_chain_of_thought(candidate: Candidate, rng: random.Random) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    new.meta["chain_of_thought"] = not new.meta.get("chain_of_thought", False)
    return new


def swap_examples(candidate: Candidate, rng: random.Random) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    if new.examples_subset is not None and len(new.examples_subset) >= 2:
        i, j = 0, 1
        new.examples_subset[i], new.examples_subset[j] = new.examples_subset[j], new.examples_subset[i]
    return new


def trim_examples(candidate: Candidate, rng: random.Random) -> Candidate:
    new = Candidate(candidate.id, list(candidate.sections), list(candidate.examples_subset or []), dict(candidate.meta))
    if new.examples_subset:
        new.examples_subset = new.examples_subset[:-1]
    return new


def section_crossover(a: Candidate, b: Candidate, rng: random.Random) -> Candidate:
    cut_a = rng.randint(0, len(a.sections))
    cut_b = rng.randint(0, len(b.sections))
    sections = a.sections[:cut_a] + b.sections[cut_b:]
    return Candidate("x", sections, a.examples_subset, {})


OPERATORS: Dict[str, Callable[..., Candidate]] = {
    "edit_constraints": edit_constraints,
    "reword_objectives": reword_objectives,
    "reorder_sections": reorder_sections,
    "toggle_chain_of_thought": toggle_chain_of_thought,
    "swap_examples": swap_examples,
    "trim_examples": trim_examples,
    "section_crossover": section_crossover,
}
