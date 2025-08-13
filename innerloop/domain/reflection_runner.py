from __future__ import annotations

import asyncio
from typing import Dict, List

from ..settings import get_settings
from .engine import get_provider_from_env

# Minimal role-specific prompt templates (short, deterministic, no CoT).
ROLE_TEMPLATES = {
    "author": (
        "[ROLE] Author\n"
        "[TASK] Draft a single improved prompt for the target task.\n"
        "[CONSTRAINTS] Be clear, concise, no chain-of-thought.\n"
        "Base:\n{base}\n\nExamples:\n{examples}\n"
        "[OUTPUT] Return ONLY the revised prompt text."
    ),
    "reviewer": (
        "[ROLE] Reviewer\n"
        "[TASK] Identify 3 concrete issues with the prompt and 3 actionable fixes.\n"
        "[CONSTRAINTS] Bullet points, terse.\n"
        "Prompt:\n{base}\n\nExamples:\n{examples}\n"
        "[OUTPUT] One line per item."
    ),
    "planner": (
        "[ROLE] Planner\n"
        "[TASK] Propose a short edit plan (≤3 edits) to strengthen the prompt.\n"
        "[CONSTRAINTS] Use operator names if possible: reorder_sections, trim_examples, swap_examples, toggle_chain_of_thought.\n"
        "Prompt:\n{base}\n\nExamples:\n{examples}\n"
        "[OUTPUT] JSON list of edit ops with optional args."
    ),
    "revision": (
        "[ROLE] Reviser\n"
        "[TASK] Apply the edit plan to produce the final revised prompt.\n"
        "Prompt:\n{base}\n\nEdit plan:\n{plan}\n"
        "[OUTPUT] Return ONLY the revised prompt text."
    ),
}


def _fmt_examples(examples: List[dict] | None, k: int = 4) -> str:
    if not examples:
        return "none"
    rows = []
    for ex in examples[:k]:
        inp = str(ex.get("input", ""))[:120]
        exp = str(ex.get("expected", ex.get("output", "")))[:120]
        rows.append(f"- input: {inp} | expected: {exp}")
    return "\n".join(rows) or "none"


async def run_reflection(
    prompt: str,
    mode: str,
    iteration: int,
    *,
    examples: List[dict] | None = None,
    target_model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Dict[str, List | Dict | str]:
    settings = get_settings()

    # Build role-specific prompt
    base = prompt.strip()
    ex_txt = _fmt_examples(examples)
    template = ROLE_TEMPLATES.get(mode, ROLE_TEMPLATES["author"])
    role_prompt = template.format(base=base, examples=ex_txt, plan="(none)")

    # In stub mode, stay deterministic and fast.
    if settings.USE_MODEL_STUB:
        await asyncio.sleep(0)  # cooperative
        proposal = (base or "stub") + f" [gen-{iteration}:{mode}]"
        # Minimal deterministic edits so apply_edits has something to do.
        edits = [{"op": "reorder_sections", "args": {}, "seed": iteration}]
        lessons = [f"{mode}: keep instructions crisp"]
    else:
        provider = get_provider_from_env(settings)
        # Pass model when provided; providers ignore unknown kwargs.
        proposal = await provider.complete(
            role_prompt, model=target_model
        )  # type: ignore[call-arg]
        edits = [{"op": "reorder_sections", "args": {}, "seed": iteration}]
        lessons = [f"{mode}: revision applied"]

    return {
        "mode": mode,
        "summary": f"{mode} summary {iteration}",
        "proposal": proposal,
        "lessons": lessons,
        "diagnoses": [],
        "edits": edits,
        "meta": {"iteration": iteration},
    }
