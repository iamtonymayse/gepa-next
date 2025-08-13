from __future__ import annotations

from collections import Counter
from typing import List


def update_lessons_journal(existing: List[str], new: List[str], max_chars: int = 2000) -> List[str]:
    freq = Counter(existing)
    freq.update(new)
    ordered = [lesson for lesson, _ in freq.most_common()]
    result: List[str] = []
    total = 0
    for lesson in ordered:
        needed = len(lesson) + (1 if result else 0)
        if total + needed > max_chars:
            break
        result.append(lesson)
        total += needed
    return result
