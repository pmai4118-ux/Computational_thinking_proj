PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES (1, '2026-11-16T00:00:00Z');

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id TEXT PRIMARY KEY,
    owner_token_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    level TEXT NOT NULL,
    state TEXT NOT NULL,
    question_refs_json TEXT NOT NULL,
    current_index INTEGER NOT NULL,
    answer_refs_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_version INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    client_submission_id TEXT,
    PRIMARY KEY (answer_id, revision),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_session_submission
ON answers (session_id, client_submission_id)
WHERE client_submission_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS evaluation_reports (
    evaluation_id TEXT PRIMARY KEY,
    input_digest TEXT NOT NULL UNIQUE,
    answer_id TEXT NOT NULL,
    answer_revision INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    question_version INTEGER NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evaluation_reports_answer_ref
ON evaluation_reports (answer_id, answer_revision);