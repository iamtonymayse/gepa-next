from __future__ import annotations

import re
from typing import Iterable, List

SENT_SPLIT = re.compile(r"[.!?]\s+")


def _first_sentence(text: str, max_len: int) -> str:
    if not text:
        return ""
    parts = SENT_SPLIT.split(text.strip(), maxsplit=1)
    s = (parts[0] if parts else text).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def distill_lessons(feedback_items: Iterable[str], max_len: int = 120) -> List[str]:
    """Distill free-form feedback strings into concise, de-duplicated lessons."""
    out: List[str] = []
    seen: set[str] = set()
    for fb in feedback_items:
        s = _first_sentence(fb or "", max_len)
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out
