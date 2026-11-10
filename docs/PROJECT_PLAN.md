# Application delivery plan

Planning date: 5 November 2026. P01 scope baseline: [MVP scope](scope.md), recorded 9 November 2026; team walkthrough and confirmation remain pending. Companion: [small task backlog](TASK_BREAKDOWN.md).

## 1. Confirmed requirements and remaining decisions

The team has eight people and approximately three to four weeks. The user will assign people to tasks. Build a browser application with a Python backend, a Vietnamese interface, technical interview practice, rubric results, answer evidence, feedback, and suggested exercises. Preserve the existing MVC-S directory names and responsibilities.

Confirmed question-sourcing decision: select questions/material from open-source resources, retain original text and license/source metadata, and review translations, adaptations and rubrics before importing. See [question source workflow](QUESTION_SOURCES.md). Google AI Studio / Gemini is the provisional AI choice. Budget, account quota, exact model, hosting, required classroom technologies, daily availability, and the final submission date remain undecided. Do not commit to paid usage until the budget is selected. This plan makes no assignments to named people.

P01 MVP baseline (see [scope and remaining decisions](scope.md)):

| Decision | MVP baseline | Remaining note |
| --- | --- | --- |
| Audience | Software Engineering students preparing for Backend Intern/Fresher interviews | Team confirmation remains pending |
| Interview format | Vietnamese text answers; four questions per session; fixed coverage | Adaptive probing is deferred |
| Question coverage | Programming knowledge, technical case, algorithm explanation in prose, technical reasoning/trade-offs | Revised by the user on 10 November 2026; C01 supplies approved skill IDs |
| Content size | Eight reviewed questions minimum, twelve target; at least two variants per category | Validate against assigned team capacity |
| Identity | Anonymous local browser session with synthetic demonstration profiles | Account system is outside the MVP |
| Operation | One Python server, same-origin pages/API, local SQLite | Hosting and classroom requirements remain open |
| Release | Local demonstration first | Hosted release only if required |

## 2. Product boundary

User scope revision, 10 November 2026: all student answers are prose. Remove coding
tasks, live-coding, code editors/submissions/storage, LeetCode handoff, sandbox
execution and vibe coding / AI-code critique. Algorithm topics are explanation
only. Rubric/evidence evaluation of text answers and failure-safe persistence
remain required. The current [specification](PROJECT_SPEC.md) supersedes older
coding requirements; legacy content examples must not be imported as current seeds.

The first release must let a student start a practice session, answer questions, receive rubric-based results linked to their original answer, understand an observed gap, and open a reviewed exercise addressing that gap. The application must recover from an AI request failure without losing the submitted answer.

Include session history in the same anonymous browser session and a retry using a different reviewed question when available. Explain results as performance on the selected questions. Do not present a hiring prediction or an overall competence diagnosis from one answer.

Later options: JD-to-skill mapping, study schedules, multi-session skill trends, adaptive probing, and a bounded Decision Replay. Broad job-market collection, multiple career tracks, voice input, screen monitoring, arbitrary code execution, a complete course recommender, and automatic question generation are outside the proposed first release. These are product choices to revisit, not requirements inferred from the draft proposal.

## 3. Delivery sequence and gates

Use relative weeks until the actual deadline is known. Plan to have a demonstrable core by the end of Week 3; use Week 4 for validation and polish. Estimates in the backlog are person-hours, not calendar promises. Check capacity after assigning tasks: eight people x available hours per week x remaining weeks, with about 25% reserved for integration, review, and unexpected work.

The 53 MVP tasks total approximately 121-199 focused person-hours before separate review and coordination. With 25% of capacity reserved, budget roughly 160-265 person-hours overall: around 7-11 hours per member per week for three weeks, or 5-9 for four weeks. This is a capacity estimate to validate with the team, not a guarantee. The 12 optional tasks are excluded from that total.

| Window | Team result | Exit condition | Backlog |
| --- | --- | --- | --- |
| Days 1-2 | Shared scope, flows, data and API contracts; one representative question | Everyone builds against the same example payloads and agreed boundaries | P01-P08 |
| Week 1 | Application skeleton and a one-question practice flow | A student can submit an answer, evaluate it with the fixture provider, save the result, and see it in the UI | F01-F06, C01-C06, U01-U02. Start the work needed for one question in E01-E02, E05-E07, E09, I01-I04, and U03-U04 |
| Week 2 | Live Gemini adapter, deterministic scoring, persistent sessions, results and exercises | One complete four-question session works. Failure and retry preserve the answer | Finish E01-E09, I01-I06, and U03-U07 |
| Week 3 | Feature-complete MVP, evaluation report, usability fixes, demo and documentation | Core acceptance checks pass and another teammate can run it from the README | U08, Q01-Q08 |
| Optional Week 4 | Reliability, rubric calibration, rehearsal and selected small improvements | Release evidence is current; no unresolved critical issue in the core flow | Rework from Q tasks; optional X tasks only after the release gate |

Use the [backlog dependencies](TASK_BREAKDOWN.md) to schedule work. Start the first integrated flow from the question and rubric in P05. Connect the fixture provider, validation, scoring, persistence, and session endpoints to a minimal answer form and result page. Content review and AI validation advance in parallel with UI work.

For a three-week deadline, keep the core feature set, eight reviewed questions, local release, and template-based feedback. Cut optional extensions and visual extras first. If capacity still does not cover the core, reduce the content target or session length explicitly and update acceptance checks; do not silently ship incomplete rubric handling.

## 4. Workstreams for team task selection

These are work areas, not assignments. Eight members can take separate tasks from them, and multiple members can share an area. Assign one implementer and a different reviewer to each task. Avoid assigning a person only to one MVC-S layer for the entire project: features need coordinated contracts and integrated demonstrations.

| Workstream | Outputs | Main collaboration |
| --- | --- | --- |
| Product and integration | Scope, contracts, session rules, connected application | All streams agree on payloads before implementation |
| Question and rubric content | Reviewed questions, skill IDs, evidence rules, answer examples | AI/scoring and QA independently review content |
| Domain and persistence | Domain records, repository interfaces, SQLite implementation | Services agree on transactions and immutable versions |
| AI and scoring | Provider adapter, evidence validation, deterministic scores | Content defines semantics; QA checks agreement |
| Session API | Controllers, sessions, answer lifecycle, retry | UI consumes stable response contracts |
| UI/UX | Vietnamese screens, shared styles, evidence navigation | Product and QA review the actual student flow |
| Exercise recommendation | Reviewed exercise catalog, gap-to-exercise rules | Content maps skills; scoring provides observed gaps |
| Quality and delivery | Automated checks, usability review, evaluation report, demo | Every feature contributes its own checks |

Suggested board columns: Ready, In progress, Review, Integrated, Done, Blocked. A merged task reaches Done only when its acceptance check is demonstrated. Use small branches such as `codex/interview-form` or the team's agreed branch convention. Integrate daily. Freeze contract changes behind a short recorded decision and update affected fixtures together.

## 5. Student flow and UI/UX

Primary flow: welcome -> practice setup -> question workspace -> answer review -> session results -> exercise -> alternate practice question. Asking for a target role is useful; asking for a full CV, company, personal identity, or long-term schedule is unnecessary for this release.

| Screen | Student task and primary action | Information and recovery |
| --- | --- | --- |
| Welcome/history | Start or reopen a practice session | Explain the selected scope; show an empty state when history is empty |
| Setup | Confirm role, level and session format; start practice | Default role/level for PoC; explain approximate duration and coverage |
| Workspace | Read the situation and submit an answer | Show question, constraints, progress, textarea and submission state; preserve draft; prevent duplicate submission |
| Answer review | Understand the result; continue | Criterion status, score where supported, exact answer excerpts, explanation, unresolved points, exercise action |
| Session results | Choose the next practice step | Per-question outcomes and observed gaps with coverage; avoid a fabricated global ability score |
| Exercise | Work on the specific gap; practice again | Explain why selected, prerequisites, reviewed instructions, source, estimated duration and an alternate question if available |

Proposed design direction: a focused study workspace. Use a broad reading/writing area and a narrower evidence panel on desktop; stack them in reading order on narrow screens. Keep the question and student's answer visually distinct. Results should make a criterion and its supporting excerpt the main visual relationship. Use a structured answer form rather than building a general chat interface first.

Initial design tokens, subject to a quick team review: white `#FFFFFF` surface, pale blue `#F3F7FC` background, navy `#17324D` text, blue `#2457C5` action, green `#166534` confirmed status, amber `#8A4B08` unresolved status. Use text and icons alongside status colors. Use a Vietnamese-capable font such as Be Vietnam Pro with system sans-serif fallback, body text around 16-18px, comfortable line spacing, an 8px spacing scale, and readable line lengths. Check contrast for actual combinations before implementation approval.

Use Vietnamese action labels consistently: “Bắt đầu luyện tập”, “Gửi câu trả lời”, “Xem căn cứ”, “Câu tiếp theo”, and “Luyện tập điểm cần cải thiện”. Plan loading, empty, invalid input, provider failure, successful evaluation, partial result, and expired session states. When a request fails, say the evaluation failed; do not label the student as insufficiently skilled.

UX acceptance: complete the flow using only the keyboard; all controls have labels and visible focus; feedback status changes are announced; original answers remain available; 360px-wide layout and 200% zoom remain usable. These are scoped project checks, not an assertion of WCAG conformance.

## 6. Proposed technology and existing MVC-S layout

The F01 baseline on `main` uses Python 3.11 and locks the FastAPI, Pydantic, Jinja2, Uvicorn, and pytest dependencies in `uv.lock`. The remaining plan uses semantic HTML/CSS, a small amount of browser JavaScript, and SQLite through Python repositories. FastAPI supports templates and static assets within the existing Python repository. [Development setup](../README.md#python-development-setup) · [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/) · [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)

The tree shows the F01 baseline and the proposed application modules. The four MVC-S packages and environment are in place. F05 will wire the app factory in `main.py`.

```text
source/
  main.py                         # composition root; start/configure app
  config.py                       # load environment settings
  Model/
    question.py                   # Skill, Question, Rubric, Criterion
    interview.py                  # InterviewSession, Answer, answer lifecycle
    evaluation.py                 # CriterionCheck, Evidence, EvaluationResult
    exercise.py                   # Exercise, Recommendation
    repositories/
      interfaces.py               # repository protocols
      sqlite_repository.py        # SQL and persistence only
      schema.sql                  # initial database schema/version
  service/
    question_bank_service.py       # content validation and read workflows
    interview_service.py           # question/session business rules
    evaluation_service.py          # interpret, validate, score, save result
    scoring_service.py             # deterministic rubric calculations
    recommendation_service.py      # observed gap -> reviewed exercises
    providers/
      interfaces.py                # EvidenceInterpreter contract
      gemini_provider.py           # Gemini calls and response translation
      fixture_provider.py          # explicit demo/test mode
    prompts/
      interpret_answer.txt          # versioned instruction template
  Control/
    schemas.py                     # HTTP request/response DTOs
    interview_controller.py         # session and answer endpoints
    evaluation_controller.py        # evaluate/retry/result endpoints
    exercise_controller.py          # exercise endpoints
  view/
    pages.py                       # page rendering routes, presentation only
    templates/                     # HTML layouts/screens
    static/css/                    # shared tokens and components
    static/js/                     # interaction and API calls
test/                              # F01 smoke tests; unit/integration checks planned
data/seed/                         # reviewed synthetic question/exercise data
docs/                              # contracts, rubric guide, QA evidence
pyproject.toml                     # F01 project and test configuration
uv.lock                            # F01 dependency lockfile
.env.example                       # variable names/placeholders only
```

Normal request: browser View calls Controller endpoint -> Controller validates shape -> Service enforces rules -> Model/repository stores data -> structured result returns to View. `main.py` constructs repositories, services, provider and controllers, mounts pages/static assets, and loads configuration. Controllers return DTOs and never import templates. `view/pages.py` renders page shells; business data comes through controllers. Model imports none of the higher layers; Service imports no View or Controller. External calls live only in Service; SQL lives only in Model repositories. Adding `repositories/` and `providers/` isolates replaceable implementations while preserving the layer layout.

## 7. Application API contract to agree before UI implementation

These are proposed internal endpoints, not existing APIs. Bind resources to the anonymous server-managed session; knowing a record ID alone must not grant access. Use same-origin browser requests and an opaque HttpOnly session cookie. For state-changing requests, include a CSRF/origin protection decision in setup; add authentication before opening this demo to real student records.

| Endpoint | Input | Structured output / rule |
| --- | --- | --- |
| `POST /api/sessions` | role, level, mode; optional owned `practice_from_answer_id` | session ID, current question, planned coverage; targeted retry derives the skill from the referenced result and excludes previously answered variants when possible |
| `GET /api/sessions/{id}` | owned session ID | state, current question and existing outcomes |
| `POST /api/sessions/{id}/answers` | question ID, original text, client submission ID | saved answer ID and state; repeated submission ID returns same answer |
| `POST /api/answers/{id}/evaluate` | owned answer ID | result or recoverable provider error; reuse existing completed evaluation |
| `GET /api/answers/{id}/evaluation` | owned answer ID | criterion checks, evidence, computed scores, feedback |
| `POST /api/sessions/{id}/next` | owned session ID | next eligible question or completed state; server enforces sequence |
| `GET /api/sessions/{id}/summary` | owned session ID | per-question outcomes, coverage, observed gaps, exercise links |
| `GET /api/exercises/{id}` | selected exercise ID | reviewed instructions, source, prerequisite IDs, duration estimate |

Separate saving from evaluating so an unavailable provider never discards the answer. For this small local demo, use a bounded server request for evaluation; no job queue is required initially. Mark concurrent evaluation as busy, prevent duplicate writes, set a timeout, and make retry reuse the saved answer. A new answer revision gets a new ID; keep the old evaluation linked to the original revision.

Define one error envelope: `code`, Vietnamese `message`, `retryable`, and `field_errors` when relevant. Distinguish malformed input, inaccessible record, invalid session transition, provider rate limit, provider timeout, invalid AI output, and storage failure. API response fields and example payloads must be finalized in P04.

## 8. Gemini API: what to call and where

Google AI Studio supplies access to the Gemini Developer API. The current official [getting-started guide](https://aistudio.google.com/docs/get-started) uses the Python `google-genai` SDK and `client.interactions.create(...)`; [structured output](https://aistudio.google.com/docs/structured-output) can constrain responses with a JSON schema. Confirm SDK/model compatibility and pin the tested version in the initial integration spike. Configure the selected model through `GEMINI_MODEL`; choose it based on account access, structured-output support, and measured quality/latency on the team's examples.

The provider adapter in `source/service/providers/gemini_provider.py` makes one structured interpretation request per submitted answer. Send only the current question, rubric criteria, original answer, and trusted task instructions. Request criterion IDs, proposed `met`/`unmet`/`insufficient_evidence` labels, literal supporting quotes or observations of missing content, and a bounded explanation. Do not ask Gemini for the final numeric score or a whole-career ability label. A schema constrains format; it does not establish that a judgment is correct.

`evaluation_service.py` checks valid criterion IDs, exactly one check per criterion, exact quote membership/locations, and required explanation fields. Reject malformed responses rather than inventing missing fields. Rubric semantics still need human calibration. `scoring_service.py` applies the versioned rules to validated checks. Feedback can be rendered from those same checks and computed results, saving a second AI call. Question selection and exercise mapping are also computed locally.

Keep `GEMINI_API_KEY` in the server environment or ignored local environment file; `config.py` reads it and `main.py` injects the configured client. Never put the real key in Python source, browser JavaScript, screenshots, or Git. `.env.example` contains placeholders only. Changing from free to paid access does not change the MVC-S design. Google documents model/account-dependent [pricing](https://aistudio.google.com/docs/pricing) and [quotas](https://aistudio.google.com/docs/rate-limits); verify the actual project limits before the demonstration. Use synthetic answers while selecting the tier and reviewing data handling terms.

Set input/output limits, one bounded transient retry, and a project request budget in configuration. A normal four-question session targets four successful interpretation calls; retries may add calls and must be counted. Log request IDs, latency, token usage when returned, and error categories without logging secrets or student answer bodies. Fixture mode must be clearly marked “Dữ liệu minh họa”; it is useful for development and provider outages, but is not evidence that live AI grading works.

## 9. Data and scoring rules

Preserve immutable question/rubric versions with each answer evaluation. Core relationships: Question -> Rubric -> Criterion; Session -> Answer -> EvaluationResult -> CriterionCheck -> Evidence; confirmed criterion gap -> skill ID -> reviewed Exercise. Evidence must point back to the original answer, including offsets when quoted. Store source URL, review status, collected/reviewed time where available, and transformation/prompt/model versions. Reference answers may guide content review but do not require students to match a single wording.

Use a small rubric-specific scale, proposed 0-2 per criterion, only after the content team defines observable level boundaries. Python maps checks to levels using declared rules. For an unresolved criterion, keep score null and show the reason. Explicitly missing required content can be unmet if the rubric defines that observation; ambiguity must not automatically become zero. For the first release show criterion results and assessable coverage, and withhold an overall total when required criteria remain unresolved. Do not compare raw totals across questions with different rubrics or infer a global skill level.

Exercise recommendations use confirmed gaps and reviewed skill mappings, order prerequisites before dependent exercises, and return an explicit no-match state if the catalog lacks a suitable exercise. Durations are estimates. Multi-session diagnosis, numeric confidence claims, and difficulty-adjusted scores need separate evidence and are later work.

## 10. Acceptance, evaluation and release

Automated behavior checks must cover rubric boundaries, alternative valid answers, missing versus ambiguous evidence, broken references, duplicate submissions, session ownership/sequence, retry, storage failures, and provider timeout/rate limit/malformed output. Mock external calls for routine tests. A controlled live API check is separate and reports the real configured model, latency, quota failures, and observed request count.

Build a minimum 24-answer synthetic evaluation set across the question categories, including correct, partial, wrong, equivalent, ambiguous and instruction-injection examples. Independently label and adjudicate expected criterion judgments. Keep development/calibration examples separate from a held-out subset; report counts. Measure criterion agreement, evidence validity, unresolved cases and per-category failure examples. Define the agreement threshold before looking at held-out results; a proposed starting target is 85% agreement on decidable labels, subject to team/lecturer review. This is a project gate, not a claim of scientific validity. Require exact quote validity and deterministic score consistency on every published result; assess semantic correctness separately.

Release gate: another teammate can install and start the app from documented commands; a complete session works; duplicate/retry and provider outage flows preserve answers; every recommendation has a traceable reason; narrow layout and keyboard flow were inspected; known limitations are documented. The final report includes architecture, data provenance, rubric examples, actual evaluation results, and the relation between decomposition, pattern recognition, abstraction, and implemented rules.

## 11. Later roadmap, gated by MVP completion

| Extension | Required groundwork | MVC-S mapping |
| --- | --- | --- |
| Adaptive next question | Validated gap rules, reviewed alternate questions, fixed minimum coverage, stop conditions | Service selection policy; Model session state; Controller next action; View explains selection |
| Decision Replay | One curated problem archetype and reviewed checkpoints/consequences; explicitly distinguish simulated outcomes | Model checkpoint data; Service trace logic; Controller replay; View timeline |
| JD-to-skill mapping | Approved source collection method, original JD preservation, normalized skill IDs, skill evidence, versioned mappings | Model job data/repository; Service extraction; Controller import; View target-role setup |
| Short learning plan | Confirmed gaps, reviewed activities, prerequisite graph, student time budget | Model plan; Service topological ordering and scheduling; Controller plan action; View calendar/list |
| Progress across sessions | Stable skill IDs, comparable tasks, evidence coverage rules; no raw score averaging | Model history; Service summaries; Controller history; View evidence-linked progress |

These extensions are not automatically included in the three-to-four-week delivery promise. Choose them only after the core release gate and capacity review.

## 12. Source basis and verification status

The plan draws on the user's confirmed answers from 5 November 2026, the repository's `AGENTS.md`, and the previously reviewed group documents. The F01 setup and smoke test results are recorded in the README. The remaining application behavior and release checks are tracked in the backlog. [Decompose](https://docs.google.com/document/d/1BiDD8ktFh-9ekP1m1435rLgpxXiJAIUwpHAtqK0GXHg/edit) · [Pattern-Recognize](https://docs.google.com/document/d/1Lt9SF7DkxAeevO7SVR-u5CwV0C07QILyH563PnpaoIU/edit) · [Abstraction](https://docs.google.com/document/d/1dr5U42ZqbVJuqsfbdvhUNiyDkXH4n-d00BjDSFr1Xxo/edit)
