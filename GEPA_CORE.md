# GEPA Core

This document outlines the first cut of the GEPA evolutionary loop.

## Example packs

Example packs live under `gepa_next/examples`. The `manifest.yaml` file lists
available packs and associated metric names. Each pack is stored as a JSONL file
with minimal fields (`question`/`answer` for QA, `text`/`label` for
classification).

## Metrics

Currently the following metrics are implemented:

* `exact_match` – normalized string comparison
* `regex_pass` – regular expression search

`evaluate_batch` caches results keyed by a content hash to keep tests fast.

## Operators

Mutation operators are exposed via `OPERATORS` and include:
`edit_constraints`, `reword_objectives`, `reorder_sections`,
`toggle_chain_of_thought`, `swap_examples`, `trim_examples`, and the crossover
operator `section_crossover`.

## Budgets

A budget controls the number of generations and rollouts. The model accepts a
payload of the form:

```json
{"budget": {"max_generations": 2, "max_rollouts": 16}}
```

Progress is reported via `budget_progress` SSE events.

## SSE events

GEPA mode streams additional events:
`generation_started`, `candidate_scored`, `frontier_updated`,
`lessons_updated`, and `budget_progress`.
