# E04: Gemini structured output

## Integration

`testE04` is based on E01. The E01 branch already contains E03 and P07, so this implementation uses their shared contracts instead of adding a second provider implementation.

The Gemini API provider sends the E03 `interpret_answer/v1` prompt with the E01 question, rubric, and answer contract. It requests JSON using `responseMimeType` and `responseJsonSchema`, validates the response at the provider boundary, and returns an `InterpretationBatch` with criterion observations, model ID, prompt version, and elapsed time. Numeric scoring remains outside the provider.

<<<<<<< HEAD
P07 selects Antigravity as the primary live provider. The Gemini API-key mode is the supported alternative and uses `gemini-2.5-flash` by default for its live check. The provider uses the standard library HTTP client as recorded in P07; no extra Gemini SDK or model override is added. API keys must be supplied through the server process environment and must not be committed.
=======
## First-time setup on Windows

Complete this setup once per computer. Run the commands from PowerShell.

### 1. Install uv

Check whether uv is already installed:

```powershell
uv --version
```

If PowerShell says `uv` is not recognized, install it with WinGet:

```powershell
winget install --id astral-sh.uv -e
```

If WinGet is unavailable, use the official Windows installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell after installation, then confirm `uv --version` prints a version. See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Open the repository and select the E04 branch

Change the path below to the folder where you cloned the repository:

```powershell
Set-Location "D:\TDTT\src\Computational_thinking_proj"
git fetch origin
```

For a first checkout of E04 in this clone:

```powershell
git switch --track -c codex/e04-gemini-structured-output origin/codex/e04-gemini-structured-output
```

If the local branch already exists:

```powershell
git switch codex/e04-gemini-structured-output
git pull --ff-only origin codex/e04-gemini-structured-output
```

Confirm the current branch:

```powershell
git status --short --branch
```

### 3. Install Python and project dependencies

The project requires Python 3.11. From the repository root, run:

```powershell
uv python install 3.11
uv sync --locked
```

`uv sync --locked` creates or updates `.venv` using `uv.lock`. This installs the app and development dependencies, including the pinned `google-genai==3.6.1` SDK and pytest. Run the import check and dependency check:

```powershell
uv run --locked python -c "from google.genai.interactions import Interaction; print('Google GenAI SDK import OK')"
uv pip check
```

If you see `ModuleNotFoundError: No module named 'google'`, run `uv sync --locked` from the repository root. A pre-existing `.venv` may not yet contain the E04 SDK. Avoid installing packages into system Python; use the project environment.

### 4. Run the local test suite

The normal suite uses mocked provider responses and does not call Gemini. Keep the live-test switch unset:

```powershell
Remove-Item Env:RUN_GEMINI_LIVE_TEST -ErrorAction SilentlyContinue
uv run --locked python -m pytest
```

Then follow the API-key setup and live-test/report instructions below.

## Model and API key
>>>>>>> c9c1b65 (Complete E04 and Instruction)

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
