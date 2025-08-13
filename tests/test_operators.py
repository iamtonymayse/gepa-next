import random

from innerloop.domain.candidate import Candidate
from innerloop.domain.operators import reorder_sections, section_crossover


def test_mutation_deterministic():
    cand = Candidate("1", ["a", "b", "c"], [])
    rng1 = random.Random(0)
    out1 = reorder_sections(cand, rng=rng1)
    rng2 = random.Random(0)
    out2 = reorder_sections(cand, rng=rng2)
    assert out1.sections == out2.sections


def test_crossover_deterministic():
    a = Candidate("a", ["x", "y"], [])
    b = Candidate("b", ["m", "n"], [])
    rng1 = random.Random(1)
    out1 = section_crossover(a, b, rng=rng1)
    rng2 = random.Random(1)
    out2 = section_crossover(a, b, rng=rng2)
    assert out1.sections == out2.sections
