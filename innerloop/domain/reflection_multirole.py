from __future__ import annotations


def update_lessons_journal(existing: str, new: str, max_chars: int = 2000) -> str:
    updated = f"{existing}\n{new}" if existing else new
    if len(updated) <= max_chars:
        return updated
    trimmed = updated[-max_chars:]
    return "..." + trimmed.lstrip()
