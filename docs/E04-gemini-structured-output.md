# E04 handoff: Gemini structured output

**Branch:** `codex/e04-gemini-structured-output`

**Task:** E04 — Integrate Gemini and parse structured JSON

**Status:** Implemented and verified with a live Gemini request and the CLI report flow.

## Model and API key

The application uses the Google GenAI Python SDK (`google-genai==3.6.1`) and defaults to model `gemini-4-hydrogen`. The model can be overridden with `GEMINI_MODEL`; the API key is read from `GEMINI_API_KEY`. Each developer creates and uses their own key. The repository does not contain a key.

Create a key in [Google AI Studio API keys](https://aistudio.google.com/app/apikey):

1. Open Google AI Studio and sign in with your Google account.
2. Open **API keys**, select **Create API key**, and follow the project prompt.
3. Copy the key. Keep it private; do not paste it into chat, source files, `.env` files committed to Git, or the repository.
4. On Windows, click the **Start button** (or press the Windows key) and search for **Edit environment variables for your account**. Open that result.
5. Click **Environment Variables…**.
6. Under **User variables** for your Windows account, click **New…**. Set the variable name to `GEMINI_API_KEY` and the value to the copied key. Do not add quotes.
7. Click **OK** in each dialog. Close and reopen PowerShell so the new process receives the variable.
8. Confirm the key is available without printing it:

   ```powershell
   if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) { "Key is missing in this terminal." } else { "Key is loaded." }
   ```

The SDK sends the key from the local environment. Do not commit it or include it in diagnostic output.

## Install and run the live CLI check

Run these commands from the repository root. If dependencies are not installed, first run `uv sync --locked`.

```powershell
$env:EVALUATION_TIMEOUT = "120"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = "localReports\e04-live-$stamp.json"

.\.venv\Scripts\python.exe -m source.main `
    --input "examples/evaluateAnswer/sampleInput.json" `
    --provider gemini `
    --output $reportPath `
    --format text
```

Use the explicit `gemini` provider. Do not pass `--recording`; recorded mode does not call Gemini. The sample input is synthetic and has `exampleOnly` set. The `120` second timeout allows for the longer live call observed during verification.

The console should show the provider/model and evaluation results, followed by `Report saved: <path>`. A timeout or other error means the evaluation did not complete and no report should be assumed to exist. Use a new timestamped path for each attempt because existing report files are not overwritten.

## Verify the saved JSON report

After the CLI succeeds, read the generated report using the same `$reportPath` value:

```powershell
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
$report | Select-Object providerName, modelName, promptVersion, providerDurationMs
"Results: $(@($report.results).Count); feedback items: $(@($report.feedbackItems).Count)"
```

For the successful live run recorded during this task, the report was `localReports\e04-live-20261122-101951.json` and contained:

- `providerName`: `gemini`
- `modelName`: `gemini-4-hydrogen`
- `promptVersion`: `criterionEvidence/1`
- `providerDurationMs`: `89775`
- Four rubric results and four feedback items

The CLI goes through the configured interpreter factory, Gemini provider, interpretation parsing, evidence validation, rubric scoring, feedback generation, and JSON repository. Saving occurs only after these steps complete. A successful report therefore demonstrates the live request and the application report path for this synthetic input.

## Verification completed

- Provider test module: **25 passed, 1 skipped** in the Codex process. The skipped test is the live test because that process did not have `GEMINI_API_KEY`.
- Full test suite: **97 passed, 1 skipped** in the Codex process, for the same environment reason.
- Live Gemini adapter test: **1 passed in 26.33 seconds** in the user's PowerShell session, using the real model.
- Full CLI live evaluation: completed and saved the report listed above; the call duration recorded in the report was 89,775 ms.

The authored sample produced Level 2 in all four competencies. This confirms that the integration and report flow ran; this one synthetic example does not establish the model's grading accuracy on a held-out dataset.

## E04 implementation outline

- `source/config.py` loads the per-user API key, model ID, and timeout from environment variables.
- `source/service/providers/gemini_provider.py` sends a structured JSON request, parses and validates the response at the provider boundary, records request duration, and maps refusal, missing output, invalid schema, timeout, and service errors.
- `source/service/providers/interpreterFactory.py` routes the CLI's `gemini` selection to the Gemini provider.
- `source/Model/evaluationData.py` defines the interpretation and report data; the report includes provider, model, prompt version, and provider duration.
- `source/service/evaluationService.py` validates evidence, scores each rubric, builds feedback, and coordinates report creation.
- `source/Model/repositories/jsonEvaluationRepository.py` writes the completed report as JSON.
- `test/service/test_gemini_provider.py` covers structured request creation, valid and invalid output, refusal and missing-output handling, settings, and the opt-in live test.

The opt-in provider live test can be run from the repository root in a PowerShell session with the key loaded:

```powershell
$env:RUN_GEMINI_LIVE_TEST = "1"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\pytest-e04-live" test/service/test_gemini_provider.py::testLiveGeminiWithSyntheticInput
```
