# E04 — Structured AI interpretation and report demo

E04 uses the E01 `EvidenceInterpreter` contract and the E03 `interpret_answer/v1` prompt. The P07 decision selects the signed-in Antigravity CLI as the primary live provider (`gemini-3.8-flash-medium`) and keeps direct Gemini REST as an optional adapter. The branch also includes a command-line path from one answer to a scored JSON report. See [E04-INSTRUCTION.md](E04-INSTRUCTION.md) for Windows setup and the exact live command.

## Provider boundary

- `source/service/providers/antigravity_provider.py` launches the local `agy` executable with a JSON schema and a signed-in user session. It requires no Gemini API key. Its response is parsed and validated as criterion observations, not numeric scores.
- `source/service/providers/gemini_provider.py` sends the same E03 prompt to Gemini REST with `responseMimeType` and `responseJsonSchema`. It reads `GEMINI_API_KEY` from the process environment, requires a configured `GEMINI_MODEL`, and uses Python's standard HTTP library (`urllib`); no `google-genai` package is required by this branch.
- `source/service/providers/factory.py` selects `antigravity`, `gemini`, or `fixture` from validated settings. The E04 CLI explicitly exposes `antigravity` and `fixture` for the report demo. The app settings default to `fixture` for offline development; the E04 CLI defaults to `antigravity`.

Both live providers return E01 criterion IDs, status, exact answer quote or omission observation, explanation, unresolved reason, model ID, prompt version, and elapsed time. They do not return a score. `source/service/evaluation_service.py` checks evidence against the saved original answer. `source/service/scoring_service.py` selects declared rubric levels and preserves an unresolved score as `null`. `source/Control/evaluation_controller.py` saves the report; `source/view/evaluation_cli.py` displays its summary.

## Acceptance evidence

From the repository root, the offline suite runs with:

```powershell
uv run --locked python -m pytest -q
```

In the November 2026 E04 handoff, this produced `53 passed, 1 skipped`; the skipped test is the optional **direct Gemini API** live check. To exercise the primary Antigravity route, sign in to `agy` and run the live CLI command in [E04-INSTRUCTION.md](E04-INSTRUCTION.md). A full synthetic answer produced 8/8; a deliberately incomplete answer produced 3/8. Both saved four criterion checks and four feedback items with exact quote locations. These runs demonstrate the command-line flow, not general scoring accuracy. Larger held-out evaluation belongs to Q03.

The direct Gemini REST adapter has mock tests for valid structured output, refusal, missing output, invalid schema, and malformed JSON. Its optional live test requires a personal API key and `RUN_GEMINI_LIVE_TEST=1`. Do not commit credentials or private student answers.

## Scope

The E04 command evaluates one JSON bundle at a time. It does not wire the web interface or provide a production quality guarantee. The shared E01/P07 interfaces remain the integration boundary for later orchestration work.
