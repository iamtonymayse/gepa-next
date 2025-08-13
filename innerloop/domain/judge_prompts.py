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

Output ONLY compact JSON on one line:
{{"winner":"A"|"B","confidence":0..1,"justification":"<≤20 words>"}}"""
