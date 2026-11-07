# Small task backlog

Companion: [overall application plan](PROJECT_PLAN.md). Date: 5 November 2026. Team: eight; deadline: approximately three to four weeks. People remain unassigned for the user to allocate. Every task starts Ready only after its dependencies and inputs are available.

## Reading and using this backlog

P0 is required for the proposed MVP. P1 extends an already working MVP. P2 is later product work. All P/F/C/E/I/U/Q tasks below are P0; X tasks have explicit priority. Estimates are rough focused person-hours including a local check, excluding a separate reviewer and coordination. Review each estimate after a short implementation spike. Split tasks exceeding one workday. Calendar planning must use actual member availability; eight members do not remove sequential dependencies.

Layer labels: M = `source/Model/`, V = `source/view/`, C = `source/Control/`, S = `source/service/`, Root = setup/composition, Content = reviewed seed data, QA = `test/` or manual evidence, Docs = planning/contract artifacts. For tables below, paths are relative to repository root. Their files are planned unless already present. A task may name multiple layers, but each layer's code keeps its own responsibility.

The 53 core tasks total 121-199 focused person-hours; reserve separate review/integration capacity as described in the overall plan. Twelve optional tasks are additional. Credential availability can block live-provider tasks without blocking fixture-based development or the initial application setup.

Each ticket should record: ID/title, implementer (unassigned), reviewer (unassigned), dependencies, exact change, relevant fixture, acceptance evidence, and status. Use the acceptance column as the initial definition of done. Combine only adjacent content tasks when workload is small; do not hide integration work inside UI tasks.

## P. Decisions and shared contracts — Days 1-2

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| P01 | Confirm role, level, four question categories and excluded features | Docs: `docs/scope.md` | — | 1-2 | One written scope and the approximate deadline are agreed |
| P02 | Draw the six-screen student flow, including provider failure and retry | V/Docs: `docs/user_flow.md` | P01 | 2-3 | Every screen has a primary action, next state and recovery path |
| P03 | Define domain records, IDs, versions and evaluation status enums | M/Docs: `docs/data_contract.md` | P01 | 2-3 | One question/answer/result/exercise example has valid links |
| P04 | Specify internal endpoints and example success/error payloads | C/Docs: `docs/api_contract.md` | P02,P03 | 2-3 | UI and backend can use identical fixtures; ownership/retry semantics included |
| P05 | Write a full rubric for one representative case question | Content/S: `data/seed/` sample | P01,P03 | 2-4 | Observable level boundaries and correct/partial/ambiguous examples reviewed |
| P06 | Establish UI direction, Vietnamese vocabulary and design tokens | V: `docs/ui_direction.md` | P02 | 2-3 | Workspace/results wireframes reviewed at narrow and desktop widths |
| P07 | Check Gemini account access, structured-output support, selected SDK/model, quota and budget decision | S/Docs: `docs/ai_decision.md` | P03,P05 | 2-4 | A minimal synthetic request is assessed if credentials are available; otherwise a clearly recorded blocker and fixture mode; no paid-tier assumption |
| P08 | Agree branch/review routine, board and completion criteria | Docs: team working agreement | P04 | 1 | Each Ready task has a clear contract and someone can claim/review it |

## F. Foundation and persistence — Week 1

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| F01 | Add dependency manifest, package initialization and development setup | Root: `pyproject.toml`, package files, README | P01,P03 | 2-3 | Another member can install the pinned baseline; provider dependency is finalized with P07 independently |
| F02 | Implement typed domain records and invariants | M: `question.py`, `interview.py`, `evaluation.py`, `exercise.py` | P03,F01 | 3-4 | Fixtures reject broken IDs/statuses and preserve null versus zero |
| F03 | Define repository protocols for content, sessions and evaluations | M: `repositories/interfaces.py` | F02 | 2-3 | Services can use in-memory fakes without SQLite imports |
| F04 | Create versioned SQLite schema and repository read/write operations | M: `repositories/schema.sql`, `sqlite_repository.py` | F03 | 3-5 | A session, original answer and versioned evaluation survive reopening the DB |
| F05 | Configure and connect an app factory, routers and dependencies | Root: `source/main.py`, `config.py` | F01,F03 | 2-3 | Page shell and health response work; dependency injection accepts fakes |
| F06 | Add ignored local DB/secret paths and placeholder environment configuration | Root: `.env.example`, targeted `.gitignore` update | F01 | 1-2 | Real secrets/DB are excluded; missing key gives a clear setup error in live mode |

## C. Reviewed content and fixtures — Week 1 into Week 2

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| C01 | Define stable skill IDs and the fixed session coverage blueprint | Content/S: seed skill/blueprint records | P01,P03 | 2-3 | Each question category has an explicit assessed skill and eligible criterion types |
| C02 | Curate two open-source programming-knowledge questions with reviewed rubrics | Content: `data/seed/questions.*` | P05,C01 | 2-4 | Both accept equivalent answers; sources and review metadata recorded |
| C03 | Curate/adapt two open-source technical-case variants with reviewed rubrics | Content | P05,C01 | 3-5 | Shared underlying concept and meaningful scenario differences reviewed |
| C04 | Curate two open-source algorithm questions with reviewed rubrics | Content | P05,C01 | 2-4 | Correctness, explanation and complexity requirements match each question |
| C05 | Select reusable open-source code for two reviewed AI-code-critique exercises | Content | P05,C01 | 2-4 | Code is presented as material to analyze; expected defects/checks reviewed |
| C06 | Build the exercise catalog and criterion-gap mappings | Content/M: `data/seed/exercises.*` | C01,P05 | 3-4 | Each seeded gap has a reviewed exercise, prerequisite IDs and duration estimate |
| C07 | Prepare 24 synthetic answer examples and independent expected judgments | Content/QA: `test/fixtures/` | C02,C03,C04,C05 | 4-6 | Correct, partial, wrong, equivalent, ambiguous and injection cases represented; calibration/held-out split recorded |
| C08 | Validate and import seed data; report individual bad records and dataset-wide failures | S/M: `question_bank_service.py`, import command | F04,C02,C03,C04,C05,C06 | 2-4 | Bad IDs/rubrics/sources have useful context; invalid required coverage blocks release |

Content work can be split by question category across teammates. A separate member reviews each rubric before it enters the bank. A one-question slice can use P05 before C02-C08 are complete.

## E. AI interpretation, scoring and feedback — Weeks 1-2

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| E01 | Define `EvidenceInterpreter` input/output interface | S: `providers/interfaces.py` | F02,P05 | 1-2 | Contract carries criterion IDs, observations, quotes and unresolved reasons, with no final numeric score |
| E02 | Implement deterministic fixture provider and visible demo-mode metadata | S: `providers/fixture_provider.py` | E01 | 1-2 | Full flow is developable without credentials; fixture output is labeled |
| E03 | Write and version the answer interpretation prompt | S: `prompts/interpret_answer.txt` | E01,P05 | 2-3 | Task instructions are distinct from answer data; equivalent/ambiguous content handled explicitly |
| E04 | Implement the Gemini adapter with structured response parsing | S: `providers/gemini_provider.py` | E01,E03,P07 | 3-5 | Synthetic call passes agreed schema using pinned SDK/model; account block remains explicit if unresolved |
| E05 | Validate criterion coverage and evidence against the saved original answer | S: `evaluation_service.py` | E01,F02 | 3-4 | Unknown/missing/duplicate criterion IDs and fabricated quotes are rejected |
| E06 | Implement rubric-specific score calculation and unresolved-result handling | S: `scoring_service.py` | P05,F02 | 3-4 | Boundary fixtures reproduce declared rules; unresolved evidence keeps null and does not produce an invented total |
| E07 | Render structured feedback from validated checks and calculated results | S: feedback builder in `evaluation_service.py` | E05,E06 | 2-3 | Each issue and explanation refers to the same criterion/evidence/result |
| E08 | Add timeout, bounded transient retry, request budget and redacted telemetry | S/config: provider wrapper/settings | E04,F06 | 2-4 | Rate limit, timeout, refusal and invalid output remain distinguishable; retry cannot loop indefinitely |
| E09 | Coordinate interpretation -> validation -> scoring -> persistence | S/M: `evaluation_service.py`, repositories | E02,E05,E06,E07,F04 | 3-4 | Fixture-based answer produces one stored result; live mode plugs in after E04/E08; failed processing never becomes an ability score |

## I. Session behavior and controllers — Weeks 1-2

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| I01 | Implement fixed question selection and valid session transitions | S: `interview_service.py` | F02,C01,P05 | 2-4 | Coverage is enforced; no repeats when eligible alternatives exist; insufficient bank is reported |
| I02 | Add create/read session controller endpoints and anonymous session binding | C: `schemas.py`, `interview_controller.py` | I01,F05,P04 | 2-3 | Valid request starts practice; invalid input and foreign session IDs are rejected |
| I03 | Save submitted answers with versioning and idempotent submission IDs | C/S/M: interview endpoint/service/repository | I02,F04 | 3-4 | Repeated submit returns the same saved answer; original text is unchanged |
| I04 | Add evaluate/read-result endpoints and safe retry/concurrency rules | C/S/M: `evaluation_controller.py`, service/repository | I03,E09 | 3-4 | Saved answer can be retried; completed result is reused; overlapping requests cannot duplicate results |
| I05 | Add next-question and session-summary workflows | C/S: interview controller/service | I04,I01 | 2-4 | Server enforces progress and returns evidence-linked outcomes with coverage |
| I06 | Select reviewed exercises for confirmed gaps and expose exercise details | S/C: `recommendation_service.py`, `exercise_controller.py` | C06,F04,E06,P04,I01 | 2-4 | Recommendation explains gap/prerequisite match; no-match/unknown states explicit; starting practice from an owned answer targets that gap with an eligible alternative |

## U. Vietnamese interface — Weeks 1-3

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| U01 | Build base template, shared tokens and labeled components | V: `templates/base.html`, `static/css/` | P06,F05 | 2-4 | Responsive page shell, visible focus and Vietnamese font rendering inspected |
| U02 | Build welcome/history and setup screens against contract fixtures | V: `pages.py`, templates, JS | U01,P04 | 2-3 | Start/reopen actions and empty history work against fixtures |
| U03 | Build question/answer workspace with draft preservation | V: templates/JS | U01,P04 | 3-5 | Question, constraints, progress and answer form work by keyboard; draft survives a failed request |
| U04 | Build criterion results and exact evidence navigation | V: answer-review template/JS | U03,P04 | 3-5 | Selecting a criterion reveals matching original answer excerpt; unresolved status readable |
| U05 | Build session summary with coverage and next-action links | V: summary template/JS | U04,P04 | 2-3 | Partial and complete sessions display correctly; absent evidence is not represented as a score |
| U06 | Build exercise detail and alternate-question action | V: exercise template/JS | U05,P04 | 2-3 | Student sees reason, prerequisite and duration estimate; unavailable alternatives have a clear state |
| U07 | Connect screens to live application endpoints | V: API client/interaction JS | U02,U03,U04,U05,U06,I02,I04,I05,I06 | 3-5 | Entire flow works with fixture provider; live provider uses identical contract |
| U08 | Complete all loading, empty, failure, retry and session-expiry states | V/C: templates/JS and error DTO alignment | U07,E08 | 2-4 | Input retained on recoverable failure; duplicate clicks prevented; errors give a next action |

U02-U06 can advance using shared JSON fixtures while backend work continues. Connect each screen as its endpoint is ready; U07 is the final integration pass, not the first integration day.

## Q. Verification and delivery — continuously, completed in Week 3

| ID | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- |
| Q01 | Establish pytest setup and focused rubric/evidence checks | QA: `test/` | F01,E05,E06 | 3-4 | Score boundaries, null handling, alternate answers and invalid quotes checked locally |
| Q02 | Add repository and API workflow checks with mocked provider | QA: `test/` | I04,I05,I06 | 3-5 | Persistence, ownership, sequence, duplicate submit, concurrent retry and rollback cases verified |
| Q03 | Run a controlled live-provider check and held-out answer evaluation | QA/Docs: `docs/evaluation_report.md` | E04,E08,C07,E09 | 3-5 | Actual model, per-category agreement, sample counts, unresolved cases, latency and failures reported; no fixture results labeled live |
| Q04 | Inspect the complete flow at narrow/desktop widths, 200% zoom and keyboard-only input | QA/V: `docs/usability_check.md` | U08 | 2-4 | Evidence navigation, focus, labels, status announcements and recovery checked; findings assigned |
| Q05 | Have several students/teammates unfamiliar with the UI complete the task | QA/Docs: observation notes | U07 | 2-3 | Record task completion, confusion and issues using synthetic answers; revise highest-impact problems |
| Q06 | Fix release-blocking failures and rerun affected checks | Relevant layer + QA evidence | Q01,Q02,Q03,Q04,Q05 | 4-8 | Core flow/recovery blockers closed; remaining limits visible |
| Q07 | Write installation, configuration, content-import and demo instructions | Docs: README, `docs/demo_script.md` | F05,C08,U07 | 2-3 | Fresh setup works on another member's machine; fixture/live modes and key setup explicit |
| Q08 | Freeze the release, rehearse and package CT/architecture evidence | Docs/Root: release checklist/report | Q06,Q07 | 2-4 | Four-question demonstration works; limitations, provenance, evaluation data and MVC-S diagram available |

Testing owners should prepare fixtures as each feature arrives. Q01/Q02 are completion points for coordinated suites, not instructions to delay all testing until Week 3.

## X. Optional tasks after the MVP gate

| ID | Priority | Small task | Layer / output | Depends | Hours | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| X01 | P1 | Add a third reviewed variant for each question category | Content | C08,Q08 | 3-5 | Four new questions pass rubric/source review and seed validation |
| X02 | P1 | Write one curated Decision Replay checkpoint scenario | Content/M | Q08 | 2-3 | Decisions and consequences reviewed, including stated assumptions |
| X03 | P1 | Implement replay traversal and a simple timeline | S/C/V | X02 | 3-5 | Only curated consequences shown; original answer/evaluation preserved |
| X04 | P1 | Specify adaptive selection rules, coverage floor and stop conditions | S/Docs | Q08 | 2-3 | Unknown evidence triggers clarification; no endless probing |
| X05 | P1 | Implement and inspect one adaptive follow-up path | S/C/V/QA | X04,X01 | 3-5 | Same skill can be probed with a reviewed alternative; choice explained |
| X06 | P2 | Define original JD schema and allowed import sources | M/Docs | Q08 | 2-3 | Source/publication/collection metadata and normalization versions preserved |
| X07 | P2 | Add manual JD text import and evidence-backed skill mapping | S/C/V | X06 | 4-6 | Original data retained; normalized skills point to original excerpts; failures reported |
| X08 | P2 | Define prerequisites, activity durations and time-budget constraints | M/Content/S | Q08,C06 | 2-4 | Cycles/unknown prerequisites and infeasible budgets have declared behavior |
| X09 | P2 | Build deterministic short learning-plan ordering | S | X08 | 3-5 | Prerequisites precede activities; impossible deadlines are reported |
| X10 | P2 | Add learning-plan action and list/calendar interface | C/V/QA | X09 | 3-5 | Each activity explains gap/prerequisite reason and labels time as an estimate |
| X11 | P1 if required for submission | Choose hosting, persistent storage and account/session safeguards | Root/M/C/Docs | Q08 | 3-5 | Costs, data handling, storage and release requirements documented before deployment |
| X12 | P1 if hosting required | Configure hosted environment and inspect release flow | Root/QA | X11 | 3-6 | Environment secrets injected; persistence/restart and access checks verified; local demo remains reproducible |

## Suggested first task wave

Begin P01 and P05's content exploration immediately, then finalize P02/P03 before P04. Once the scope and sample are agreed, team members can claim P06, P07 and early foundation/content tasks. P05 is not finalized before P03: exploration can start early, but the shared schema governs its final format. The first integration target is P05 + E02 + F04 + I03/I04 with a minimal answer/result View. Demonstrate that one-question path before increasing content volume or polishing all screens.

## Definition of a completed implementation task

1. Files are in the correct MVC-S layer; dependencies respect `AGENTS.md`.
2. Expected behavior and important failure cases were checked with relevant examples.
3. Content/provenance/version fields and null/unknown semantics remain intact.
4. A separate reviewer can reproduce the acceptance evidence.
5. Affected contract, seed data and setup instructions agree with the final change.
6. Integration is demonstrated in the current application; remaining limitations are explicit.

This document is a planned backlog. No task is marked implemented or tested by the creation of this file.

