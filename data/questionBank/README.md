# Ten-question PoC catalog

`catalog.json` is a versioned, illustrative selection from the existing Task 3
dataset. Source commit: `9106f6d44a8e03ec8d7894a443679de2f0b2f05f`.
`upstream/` preserves the six source JSON snapshots. Runtime reads the catalog
through `JsonQuestionRepository`; it does not execute Git or require a branch.

Four questions cover Knowledge, Analysis, Testing, Implementation; six cover a
subset. Each applicable dimension has one rubric with two observable checks.
The 0/1/2 levels use explicit gates, not a cumulative requirement for mutually
exclusive source levels. These are newly authored PoC rubrics, not a lossless
adapter for the original source rubric. Original content and adaptation notes
are separate. Source hashes use canonical JSON (`sort_keys=True`, UTF-8,
`ensure_ascii=False`, separators `(',', ':')`).

All questions are pending review. Five synthetic sample answers per question
cover complete, partial, wrong/missing, equivalent presentation, and ambiguous
responses. Recordings contain exact input digests and evidence offsets. Their
proposed labels are implementation fixtures, not independent ground truth.

## Review workflow

1. The Task 3 owner checks each original prompt against its adapted question,
   rubric checks and score boundaries. Confirm applicability of all four groups.
2. Verify source URL, author/license information and permitted use. A reference
   URL alone does not establish a license. Preserve unresolved metadata as null.
3. A reviewer different from the curator reads every full sample answer and its
   question/rubric. Use `reviewWorksheet.csv` for judgments and disagreements;
   inspect `catalog.json` for full text. Review quotes in context, not in isolation.
4. Review both checks per applicable dimension, exact quote/offset, omissions,
   ambiguity, computed score and generated feedback. For code questions, inspect
   or execute the examples independently; this evaluator does not execute code.
5. Resolve disagreements. A question/rubric change increments its version. A
   changed sample or input requires a freshly matched recording/input digest.
   Never transplant a recording from another answer or leave a stale digest.
6. Only after real verification, set sample `referenceStatus=human_reviewed`,
   source `licenseStatus=verified` with license ID/URL and source URL, review
   checks (`sourceAndLicense`, `technicalCorrectness`, `rubricBoundaries`,
   `equivalentAnswers`, `referenceAnswers`) to true, reviewer/date and
   `status=approved`, and template `exampleOnly=false`. Recompute recording
   digests because `exampleOnly` is part of the input snapshot. Retain the review
   worksheet as the evidence for these declarations.
7. Run the tests and recorded previews, then assess new answers live against the
   independent judgments. Report disagreements separately from provider failures.

Do not fill approval metadata automatically. `QuestionBankService` enforces the
required declarations but cannot establish that a human actually performed them.
`demoMode=False` rejects pending content. The current web entry intentionally
uses labeled demo mode; production session/account integration remains separate.
