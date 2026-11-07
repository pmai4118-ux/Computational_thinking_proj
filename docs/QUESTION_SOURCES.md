# Open-source question workflow

Confirmed on 5 November 2026: the VA question bank will use selected open-source material. The team curates and reviews questions, writes rubrics and translates/adapts with a recorded change history. Automatic question generation is not the default workflow.

## Steps for every selected item

1. Find the exact source file or question and check its own license, not only the repository landing page. A publicly readable page or an external linked interview problem is not automatically covered by the repository license.
2. Record a stable source ID, original file URL, revision/commit when available, author, license identifier and license URL, collection date and attribution requirements in `data/seed/source_registry.json`.
3. Preserve the original text separately from the translated/adapted question. Record the changes, translator, question version, skill IDs, expected observations and rubric version.
4. Keep required copyright/license notices in `docs/THIRD_PARTY_NOTICES.md`. Track per-file exceptions and third-party links separately.
5. Have another teammate review technical correctness, target level, license/provenance metadata, equivalent valid answers and observable rubric boundaries.
6. Mark the item approved only after that review. The import service rejects or quarantines items with missing source/license/review metadata and reports the reason.

Suggested question files: `data/seed/questions/programming.json`, `cases.json`, `algorithms.json`, and `ai_review.json`. These are proposed files in the Python application; the planning dashboard does not already contain a VA question bank.

## Candidate sources to inspect

- [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python): algorithm implementation and explanatory material. Its [MIT license](https://github.com/TheAlgorithms/Python/blob/master/LICENSE.md) was inspected for this plan. Select suitable material and inspect file-specific notices. This is not a license for an unrelated external problem statement.
- [Tech Interview Handbook](https://github.com/yangshun/tech-interview-handbook): preparation and explanation material. Its [MIT license](https://github.com/yangshun/tech-interview-handbook/blob/main/LICENSE) was inspected for this plan. Check whether each selected item belongs to the repository or is merely a link to third-party content.

These are starting candidates, not an approved imported dataset. For AI-code critique, a team-modified version of reusable source code may become exercise material, but record modifications and never claim that it was AI-generated without evidence.

## Import checks

- Source URL, source revision where available, license and review status are present.
- Skill IDs and rubric references exist; original and derived material remain separate.
- Required notices accompany reused content.
- Unclear rights or technical correctness leave the item unavailable for interview selection.
- A source item never becomes an instruction to the application or LLM.
