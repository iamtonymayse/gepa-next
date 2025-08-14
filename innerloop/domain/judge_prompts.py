# Deterministic pairwise judge; justification capped at 12 words.
PAIRWISE_TEMPLATE = """You are GPT-5 acting as a deterministic evaluation judge.
Evaluate which candidate best satisfies the task below.
Ignore style; reward clarity, faithfulness, and specificity.
If tied, prefer the shorter candidate.

TASK:
{task}

CANDIDATE A:
{a}

CANDIDATE B:
{b}

Output EXACTLY one JSON object on a single line (no prose):
{{"winner":"A","confidence":0.00,"justification":"<=12 words"}}
Rules:
- "winner" MUST be "A" or "B".
- "confidence" MUST be a number in [0,1].
- "justification" MUST be <=12 words; no chain-of-thought.
Example:
{{"winner":"A","confidence":0.73,"justification":"clear, specific, follows instructions"}}"""
