# Inventory-race PoC fixtures

These synthetic examples adapt the question and constraints from `case.c03.inventory_race.v1` in `origin/p05-questionbank` at commit `9b1f2e5`. That record and its rubric remain unchanged in their branch. It is `pending_review` with no independent reviewer. The question, adaptation, judgments and expected results here are provisional and carry `exampleOnly=true`; they are not an approved question bank or benchmark.

The case references `source.c03.concurrent_inventory` in `data/seed/source_registry.json` on the same P05 branch. The registry reports the source as <https://github.com/yangshun/tech-interview-handbook>, file `system-design/concurrency.md`, revision `main-2026`, with an MIT license and authors Yangshun Tay and Tech Interview Handbook contributors. These are claims recorded by the source registry; this PoC has not independently verified the URL, file, revision, authorship, or license. The registry's own `verified` status does not replace that independent review.

The original rubric has three criteria, each with levels 0/1/2 and a possible summed total. The evaluator uses separate rubric-level scores and binary criterion checks. This PoC defines one new rubric for each original criterion:

| Original criterion | Basic check (level 1) | Additional check (level 2) |
| --- | --- | --- |
| `c03.race` | Recognize an overselling risk | Explain the shared-database interleaving across instances |
| `c03.atomicity` | Protect inventory in the shared database | Include order creation, decrement and rollback in one transaction |
| `c03.concurrent_tests` | Exercise two concurrent clients | Assert success, stock and rollback outcomes |

Level 0 is the baseline, level 1 requires the basic check, and level 2 requires both checks. This is a separately authored approximation, not a lossless conversion: positive gates cannot encode every contradictory or unsafe answer, and this PoC does not calculate the original total. A human must review the adaptation and score boundaries before comparing it with the original rubric.

Each of the five `*.input.json` files is a complete immutable input. Its `*.recording.json` is a manually specified synthetic interpretation bound to that exact input hash. The `*.expected.json` files are provisional expectations, not independently reviewed human judgments. Recorded runs exercise validation, scoring and feedback; they do not measure Gemini accuracy. The Task 3/4 team should replace or supplement these examples with independently reviewed answer variants and reference judgments before reporting model quality.

Run one recorded example from the repository root:

```powershell
uv run --locked python -m source.main --input examples/evaluateAnswer/inventoryRace/correct.input.json --provider recorded --recording examples/evaluateAnswer/inventoryRace/correct.recording.json
```

Regenerate the illustrative JSON files after an intentional change to `build_examples.py` with `uv run --locked python -m examples.evaluateAnswer.inventoryRace.build_examples`.
