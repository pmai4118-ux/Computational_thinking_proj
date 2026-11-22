# E04: Gemini structured output

## Integration

`testE04` is based on E01. The E01 branch already contains E03 and P07, so this implementation uses their shared contracts instead of adding a second provider implementation.

The Gemini API provider sends the E03 `interpret_answer/v1` prompt with the E01 question, rubric, and answer contract. It requests JSON using `responseMimeType` and `responseJsonSchema`, validates the response at the provider boundary, and returns an `InterpretationBatch` with criterion observations, model ID, prompt version, and elapsed time. Numeric scoring remains outside the provider.

P07 selects Antigravity as the primary live provider. The Gemini API-key mode is the supported alternative and uses `gemini-2.5-flash` by default for its live check. The provider uses the standard library HTTP client as recorded in P07; no extra Gemini SDK or model override is added. API keys must be supplied through the server process environment and must not be committed.

## Verification

Run the mock and contract tests:

```powershell
uv run --locked python -m pytest test/test_gemini_provider.py test/service/test_interpreter_interface.py test/service/test_prompt_template.py -q
```

Run the live check only when a Gemini API key is available in the current server environment:

```powershell
$env:RUN_GEMINI_LIVE_TEST = "1"
uv run --locked python -m pytest test/test_gemini_provider.py -k live -q
```

The live test reads `GEMINI_API_KEY` from the process environment and uses `gemini-2.5-flash`, unless `E04_GEMINI_LIVE_MODEL` is explicitly set. It does not print or save the key.

The current Codex process did not have `GEMINI_API_KEY`, so the live check was not run here. This is recorded as an environment blocker; the mock tests still verify valid structured output, E01 contract mapping, refusal, missing output, invalid schema, and malformed JSON.
