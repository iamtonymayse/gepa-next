PAIRWISE_TEMPLATE = """You are GPT-5 acting as a strict evaluation judge.
TASK: {task}
CANDIDATE A:
{a}
CANDIDATE B:
{b}
Decide the better candidate strictly for the task. Respond JSON:
{{"winner": "A"|"B", "confidence": 0..1, "justification": "<short>"}}"""
