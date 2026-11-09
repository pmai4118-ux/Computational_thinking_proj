# Computational_thinking_proj

Computational Thinking class project for a Vietnamese technical interview practice app.

## Python development setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run these
commands in PowerShell from the repository root.

```powershell
uv python install 3.11
uv sync --locked
uv run --locked python -m pytest
uv pip check
```

`uv sync --locked` creates `.venv`, installs the versions in [uv.lock](uv.lock),
and installs the local `source` package in editable mode. The runtime uses
FastAPI, Pydantic, Jinja2, and Uvicorn. The development group adds pytest and the
HTTP client used by FastAPI's test client. [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

Use imports such as `source.Control` and `source.Model` with the existing
capitalization. Pytest discovers tests under `test/`. The F01 smoke tests check
Vietnamese HTML rendering and request validation with a small test app.

Verified on Windows x64 with CPython 3.11.18. The locked install, dependency
check, and both smoke tests passed in a fresh virtual environment.

When intentionally changing dependencies, edit [pyproject.toml](pyproject.toml),
run `uv lock`, then repeat the sync and checks. Include both files in the change.

### Local configuration

[.env.example](.env.example) lists the variables for the server process. Set
them in the launching shell or have your launcher export them from an ignored
local `.env` file. `source.config.load_settings()` reads the process environment.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EVALUATION_PROVIDER` | `fixture` | Demo mode supplies the label **Dữ liệu minh họa**. Set `gemini` to require live settings. |
| `GEMINI_API_KEY` | Unset | Required for `gemini`. Inject it as a server secret. |
| `GEMINI_MODEL` | Unset | Required for `gemini`. Use the model selected in P07. |
| `GEMINI_TIMEOUT_SECONDS` | `30` | A finite positive number of seconds. |
| `DATABASE_PATH` | `.local/interview.sqlite3` | SQLite filename. Relative paths use the server's working directory. Launch from the repository root for this default. |

Keep generated databases, logs, and private student records in the ignored
`.local/` directory. F04 will own database initialization and F05 will call
`load_settings()` when it builds the app.

### Application entry point

`source/main.py` is reserved for the F05 app factory. Once F05 provides an ASGI
factory named `create_app`, the launch command will be
`uv run --locked uvicorn source.main:create_app --factory --reload`.

## Coding agent setup

- [AGENTS.md](AGENTS.md) is the shared rulebook for task scope, MVC-S boundaries,
  and acceptance checks. Codex reads it directly. [Claude Code](CLAUDE.md) and
  [Cursor](.cursor/rules/project.mdc) have entry points that refer to it.
- [Project skills](.agents/README.md) include five upstream skills and the
  repository's `$ct-task-workflow` for sprint tasks and handoffs.
- Codex can use the project profiles [`ct_task_implementer`](.codex/agents/ct_task_implementer.toml)
  for one scoped implementation task and [`ct_change_reviewer`](.codex/agents/ct_change_reviewer.toml)
  for an independent review. Ask for a profile by name when you want to delegate.
  If new profiles do not appear in an existing session, open a new session from
  the repository root.

Example requests

- “Use $ct-task-workflow to implement E05 and verify its acceptance criteria.”
- “Have ct_change_reviewer review the current diff against the E05 acceptance criteria.”

Use `docs/TASK_BREAKDOWN.md` and `docs/TASK_INSTRUCTIONS.md` to find task IDs and
acceptance criteria. If the planning files are absent from your checkout, include
the task scope and acceptance criteria in the prompt.
