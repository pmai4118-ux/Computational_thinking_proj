# Reviewed seed import (C08)

From the repository root, validate and import the bank with:

```powershell
.\.venv\Scripts\python.exe -m source.service.question_bank_service --database .local/interview.sqlite3
```

Use `--seed-dir PATH` to check a different seed directory. The command prints a JSON report with `accepted` (valid records), `imported` (new SQLite rows), `excluded`, `blocked`, and `issues`; each record issue has a code, file, zero-based array index, ID, and message. Importing an unchanged catalog again yields zero new rows. A nonzero exit code means the dataset was blocked and no content records were imported. The app uses the same validator when it seeds a fresh database.

Only approved questions, rubrics, and exercises with independent review and verified source/license metadata are imported. Example records and invalid records appear in `issues`. The import accepts valid records only if each blueprint slot still has two distinct reviewed questions and each eligible skill/criterion type has a reviewed exercise. Missing or malformed core files, duplicate core IDs, and missing required coverage block the whole dataset. SQLite commits the accepted catalog in one transaction; a conflicting immutable version rolls it back.
