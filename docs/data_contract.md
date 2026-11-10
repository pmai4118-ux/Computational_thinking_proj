# Interview practice data contract (P03 draft)

Status: proposed domain contract based on the P01 baseline in
[`scope.md`](scope.md); team walkthrough and contract review remain pending. The
MVP has four question categories and one question per category in a session.
Approved skill IDs and detailed coverage remain C01 decisions. This contract does
not make the illustrative records importable.

## Contract decisions

- An ID names one logical record and is never reused for a different record.
  Reusable content (`Question`, `Rubric`, `Exercise`) is immutable by version:
  edits keep the ID and increment the positive integer `version`. References to
  these records include both `id` and `version`.
- `Skill.id` is stable within the approved skill catalog. C01 owns the catalog;
  example IDs here are placeholders, not approved skill IDs. A criterion ID is
  stable within a rubric family; a changed criterion meaning gets a new ID.
- Each question revision points to exactly one rubric revision. An answer records
  the question revision shown to the student. An evaluation snapshots the answer
  ID/revision and the exact question and rubric revisions it assessed.
- A new answer revision is saved as a new immutable answer record, consistent
  with the proposed retry/session flow in `PROJECT_PLAN.md`. The revision number
  distinguishes it from earlier submitted text; old answer and evaluation records
  remain addressable.
- A session ID identifies the mutable session aggregate; its state changes are
  recorded over time. A result ID identifies an evaluation for an answer; each
  reevaluation creates the next immutable result version. A retry reuses a
  completed version and never overwrites the saved answer.
- IDs are opaque strings. A prefix such as `question.`, `rubric.`, or `skill.` is
  recommended for readability, but no slug syntax or ID generator is selected.
  `version` and `revision` are positive integers starting at 1.
- Source URL, source revision, author, license identifier/URL, collection time,
  curator, reviewer, and review time are retained when known. Unknown values are
  null; null does not mean verified or approved. Only reviewed content with
  verified provenance can be published to a real question bank. Approval needs
  a curator, a different reviewer, a review timestamp, and completed source,
  license, content, and rubric checks. Timestamps serialize as ISO 8601 UTC.
- P01 selects Backend Intern/Fresher preparation and the four categories listed in
  `scope.md`. The model keeps category/role/level as strings; F02/C01 boundary
  validation and approved skill IDs are still pending.

## Records and ownership

| Record | Required identity and links | Notes |
| --- | --- | --- |
| `Skill` | Stable `skill_id` | Catalog and approved IDs are C01 decisions. |
| `Question` | `question_id`, `version`, `rubric_ref`, `skill_ids`, `source_id`, review metadata | Prompt/adaptation and original source content stay distinguishable. |
| `Rubric` | `rubric_id`, `version`, criteria, review metadata | Criteria and score boundaries are versioned with the rubric. |
| `Criterion` | `criterion_id`, label, expected evidence, observable score levels | A criterion check refers to a criterion in the result's rubric version. |
| `Session` | `session_id`, state, ordered question refs, answer refs | Owner binding, expiration, legal transitions, and concurrency rules are finalized by P04/F02. |
| `Answer` | `answer_id`, `revision`, `session_id`, exact `question_ref`, original text, submission time | Keep submitted text immutable; provider failures do not replace it. |
| `Evidence` | `answer_ref` plus exact quote offsets or a bounded observation | Never treat model-generated text as a quote from the answer. |
| `EvaluationResult` | `evaluation_id`, version, status, `answer_ref`, `question_ref`, `rubric_ref`, criterion checks | Processing failure is not a student judgment. Evaluation/model/prompt versions are retained. |
| `Exercise` | `exercise_id`, version, related skills, prerequisites, source/review metadata | Durations are optional estimates; recommendation rules live in Service. |

P03 adds shared IDs in `source/Model/ids.py` and content/evaluation records in
`source/Model/question.py` and `source/Model/evaluation.py`. Session, Answer, and
Exercise Python records belong in the later F02 modules (`interview.py` and
`exercise.py`); their required links are defined here so the shared contract is
visible before those implementations exist. The modules contain data structures
only: invariants and deserialization validation are F02/import-boundary work.

## Status and null semantics

| Field/status | Meaning |
| --- | --- |
| Review `draft`, `pending_review`, `approved`, `rejected` | Editorial workflow. Only `approved` plus verified source/license review is publishable. |
| Evaluation `pending`, `processing`, `completed`, `failed` | Evaluation processing lifecycle. `failed` contains failure context and no assessment score. |
| Criterion `met` | Evidence satisfies the selected rubric level; score comes from that rubric. |
| Criterion `unmet` | Available answer evidence demonstrates a defined requirement was not met; score may be zero. |
| Criterion `insufficient_evidence` | The answer/context cannot support a judgment; `score` is null and a reason is required. |
| `total_score: 0` | A real computed zero under a decidable rubric. It must not be converted to null or omitted. |
| `score: null` / `total_score: null` | No defensible numeric judgment exists (for example, unresolved required evidence or processing failure). This is not zero. |
| Optional provenance such as `source_revision` or `license_url` is null | The value is unknown/not supplied. It does not indicate clearance. |

Each criterion declares its own allowed observable levels; this contract does not
fix a universal 0–2 scale. For this MVP proposal, a total is exposed only when all
criteria in the rubric (all required for this contract version) are decidable. If
any criterion is unresolved, keep its score and the total null while preserving
any other criterion checks. A provider/storage error is an evaluation failure,
never `unmet` or a skill gap.

Evidence quote offsets are zero-based, end-exclusive Python Unicode code-point
indices into the exact saved answer text. When a quote is supplied,
`answer.text[start_offset:end_offset]` must equal it. Observations must state what
was or was not available without pretending to be a literal quote. Each evidence
record contains exactly one form: a literal quote with both offsets, or an
observation without quote offsets.

## Linked illustrative record set

The following is one JSON-shaped fixture showing the links across question,
answer, result, and exercise. It is synthetic (`example_only: true`), has no
verified source/license or independent review, and must not be imported or shown
as reviewed content.

```json
{
  "schema_version": "p03-domain-example/1",
  "example_only": true,
  "source": {
    "id": "source.authored-demo",
    "url": null,
    "revision": null,
    "author": null,
    "license_identifier": null,
    "license_url": null,
    "license_status": "not_checked",
    "collected_at": null
  },
  "question": {
    "id": "question.python-default-demo",
    "version": 1,
    "category": "example_only",
    "language": "en",
    "prompt": "Explain when a mutable default argument is created.",
    "original_content": "Authored synthetic example; no external source.",
    "adaptation_note": null,
    "skill_ids": ["skill.python-default-demo"],
    "rubric": {"id": "rubric.python-default-demo", "version": 1},
    "source_id": "source.authored-demo",
    "review": {
      "status": "draft",
      "curator_id": "synthetic-curator",
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      }
    }
  },
  "rubric": {
    "id": "rubric.python-default-demo",
    "version": 1,
    "criteria": [
      {
        "id": "criterion.default-lifetime",
        "label": "Explains the shared default value",
        "expected_evidence": ["Default values are created when the function is defined."],
        "levels": [
          {"score": 0, "description": "Gives an incorrect explanation."},
          {"score": 1, "description": "Identifies sharing but not when the value is created."},
          {"score": 2, "description": "Explains definition-time creation and shared mutation."}
        ],
        "equivalent_answers_note": "Accept technically equivalent wording."
      }
    ],
    "review": {
      "status": "draft",
      "curator_id": "synthetic-curator",
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      }
    }
  },
  "session": {
    "id": "session.demo-01",
    "state": "completed",
    "question_refs": [{"id": "question.python-default-demo", "version": 1}],
    "answer_ids": ["answer.demo-01"]
  },
  "answer": {
    "id": "answer.demo-01",
    "revision": 1,
    "session_id": "session.demo-01",
    "question_ref": {"id": "question.python-default-demo", "version": 1},
    "text": "The default list is created again for each call.",
    "submitted_at": "2026-11-09T00:00:00Z"
  },
  "evaluation": {
    "id": "evaluation.demo-01",
    "version": 1,
    "status": "completed",
    "answer_ref": {"id": "answer.demo-01", "revision": 1},
    "question_ref": {"id": "question.python-default-demo", "version": 1},
    "rubric_ref": {"id": "rubric.python-default-demo", "version": 1},
    "criterion_checks": [
      {
        "criterion_id": "criterion.default-lifetime",
        "status": "unmet",
        "score": 0,
        "evidence": [
          {
            "answer_ref": {"id": "answer.demo-01", "revision": 1},
            "quote": "The default list is created again for each call.",
            "start_offset": 0,
            "end_offset": 48,
            "observation": null
          }
        ],
        "explanation": "The answer says the default is recreated for every call, which is incorrect.",
        "unresolved_reason": null
      }
    ],
    "total_score": 0,
    "maximum_score": 2,
    "failure_code": null,
    "failure_message": null,
    "prompt_version": "interpretation/1",
    "model_id": "fixture"
  },
  "exercise": {
    "id": "exercise.python-default-demo",
    "version": 1,
    "title": "Trace a mutable default argument",
    "related_skill_ids": ["skill.python-default-demo"],
    "prerequisite_ids": [],
    "source_id": "source.authored-demo",
    "review": {
      "status": "draft",
      "curator_id": "synthetic-curator",
      "reviewer_id": null,
      "reviewed_at": null,
      "checks": {
        "source_and_license_verified": null,
        "original_and_adaptation_preserved": null,
        "technical_correctness_checked": null,
        "rubric_levels_distinct": null,
        "equivalent_answers_checked": null,
        "review_cases_checked": null
      }
    },
    "estimated_duration_minutes": null
  },
  "recommendation": {
    "exercise_ref": {"id": "exercise.python-default-demo", "version": 1},
    "based_on_evaluation_id": "evaluation.demo-01",
    "criterion_ids": ["criterion.default-lifetime"],
    "skill_ids": ["skill.python-default-demo"]
  }
}
```

The links are valid because the answer points to question version 1; the result
points to that exact answer revision, question version, and rubric version; its
criterion ID belongs to that rubric; its evidence quotes that answer; and the
exercise/recommendation refer to the skill and evaluation gap. `total_score: 0`
is intentionally a numeric zero. An insufficient-evidence case instead uses
`score: null`, a required reason, and `total_score: null`; it is not the same
result.

Example of a rejected record (not a second valid fixture):

```json
{
  "answer": {"id": "answer.demo-01", "revision": 1},
  "evaluation": {
    "status": "completed",
    "answer_ref": {"id": "answer.missing", "revision": 1},
    "question_ref": {"id": "question.python-default-demo", "version": 2},
    "rubric_ref": {"id": "rubric.python-default-demo", "version": 1},
    "criterion_checks": [
      {"criterion_id": "criterion.unknown", "status": "insufficient_evidence", "score": 0}
    ],
    "total_score": 0
  }
}
```

Reject it because the answer reference does not resolve, question version 2 is
missing, the criterion is absent from rubric version 1, and an unresolved
criterion cannot carry score 0 or justify a computed total.

## Compatibility and remaining decisions

`QUESTION_JSON_FORMAT.md` is explicitly a pre-P03 proposal. Its `example.*.v1`
IDs put version text inside IDs and its review fixtures use a compact field shape;
the examples are not importer fixtures. Before C08/F02 consumes them, normalize
their IDs and references to this contract, preserve their illustrative-only
status, and agree the serialized schema in P04. No existing code, API payload,
or seed fixture consumes that proposal today.

P01 must still confirm the product scope. P04 must finalize API representations,
session ownership, retry/idempotency and transitions. F02 must implement the
remaining Session/Answer/Exercise classes and invariant checks. C01 must approve
skill IDs. P05 must supply a real reviewed question/rubric/source set. These
decisions remain open; this draft does not assert they have been approved.

## Addendum: answer-evaluation PoC, schema `answerEvaluation/1`

The user's newer `Abstraction.docx` and explicit implementation request require
one rubric per assessed competency, multiple rubrics per question, and a declared
multi-level score per rubric. They also permit an unknown criterion when it does
not change the uniquely determined rubric level. These differ from the P03 draft
above (one rubric per question, scores per criterion, unresolved criterion blocks
the total). The PoC does not silently reinterpret P03 totals or replace its models.

`source/Model/answerData.py` and `evaluationData.py` define a separate validated,
immutable boundary using the user's camelCase names. Existing P03 dataclasses,
IDs, examples and their future consumers stay intact. Existing ID types are reused.
No runtime consumer of the P03 question/evaluation records existed in this
checkout beyond their own type imports when the PoC was added. New consumers are
the PoC controller, service, provider adapters, CLI/view, and its focused tests.

| Addition | Reason / serialization |
| --- | --- |
| `Question.version`, `Rubric.version`, `Answer.revision` | Positive integers; report stores exact immutable input snapshots. |
| `Criterion.omissionMeansUnmet` | Explicit boolean controlling whether an observed omission can support unmet. |
| `ScoreLevel.requiredMet`, `minimumMet` | Executable positive gates and threshold; select highest matching value. Descriptions remain human-readable. |
| Evidence `type`, `quote`, `location`, `observation`, `startOffset`, `endOffset` | Exact excerpts/ambiguities or explicit omissions. Same Python Unicode offset convention as P03. |
| Result `status` | `graded` or `insufficientEvidence`; processing failures are separate errors, not fabricated results. |
| `inputHash`, input snapshots, `providerName`, `modelName`, `promptVersion` | Bind recorded interpretations and reports to exact inputs and identify illustrative versus live processing. |
| `exampleOnly` | Marks unreviewed synthetic PoC content; it does not bypass question-bank approval. |

The report has one result per rubric, one check per criterion, and one feedback
per result. Score must be a declared level or null with an explanation. No raw
cross-rubric total is produced. Results are accumulated in memory and published
only after all validations succeed; CLI writes a complete report without
overwriting an existing file. Original input files are never changed.

The new schema is **not** accepted by the existing draft question-bank JSON
format without an explicit adapter and team decision. F02/P04 integration must
agree whether to adopt this multi-rubric model or map it to P03 while preserving
versions, evidence and score semantics. There is no automatic lossy conversion.
The PoC does not mark source/license checks or independent rubric review complete.
See [the implementation guide](evaluateAnswer.md) for executable scoring semantics,
limitations and the live evaluation procedure.
