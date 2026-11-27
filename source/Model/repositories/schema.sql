-- Versioned SQLite schema for interview practice content, sessions, answers, and evaluations (F04)

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version >= 1),
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    url TEXT,
    revision TEXT,
    author TEXT,
    license_identifier TEXT,
    license_url TEXT,
    license_status TEXT NOT NULL,
    collected_at TEXT,
    required_notice TEXT
);

CREATE TABLE IF NOT EXISTS rubrics (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    criteria_json TEXT NOT NULL,
    review_json TEXT NOT NULL,
    PRIMARY KEY (id, version)
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    category TEXT NOT NULL,
    language TEXT NOT NULL,
    role TEXT NOT NULL,
    level TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    prompt TEXT NOT NULL,
    skill_ids_json TEXT NOT NULL,
    rubric_id TEXT NOT NULL,
    rubric_version INTEGER NOT NULL CHECK (rubric_version >= 1),
    source_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    review_json TEXT NOT NULL,
    original_content TEXT,
    adaptation_note TEXT,
    code TEXT,
    code_language TEXT,
    constraints_json TEXT NOT NULL,
    PRIMARY KEY (id, version),
    FOREIGN KEY (rubric_id, rubric_version) REFERENCES rubrics (id, version),
    FOREIGN KEY (source_id) REFERENCES sources (id)
);

CREATE TABLE IF NOT EXISTS exercises (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    instructions TEXT NOT NULL,
    related_skill_ids_json TEXT NOT NULL,
    prerequisite_ids_json TEXT NOT NULL,
    target_criterion_types_json TEXT NOT NULL,
    estimated_duration_minutes INTEGER,
    observable_outcome TEXT,
    source_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    review_json TEXT NOT NULL,
    PRIMARY KEY (id, version),
    FOREIGN KEY (source_id) REFERENCES sources (id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    owner_token_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    level TEXT NOT NULL,
    language TEXT NOT NULL,
    state TEXT NOT NULL,
    question_refs_json TEXT NOT NULL,
    current_index INTEGER NOT NULL CHECK (current_index >= 0),
    answer_refs_json TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    evaluation_timing TEXT NOT NULL DEFAULT 'per_question'
);

CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions (owner_token_hash);

CREATE TABLE IF NOT EXISTS answers (
    id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_version INTEGER NOT NULL CHECK (question_version >= 1),
    rubric_id TEXT NOT NULL,
    rubric_version INTEGER NOT NULL CHECK (rubric_version >= 1),
    text TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    client_submission_id TEXT,
    PRIMARY KEY (id, revision),
    UNIQUE (session_id, client_submission_id),
    FOREIGN KEY (session_id) REFERENCES sessions (id),
    FOREIGN KEY (question_id, question_version) REFERENCES questions (id, version),
    FOREIGN KEY (rubric_id, rubric_version) REFERENCES rubrics (id, version)
);

CREATE INDEX IF NOT EXISTS idx_answers_session ON answers (session_id);

CREATE TABLE IF NOT EXISTS answer_drafts (
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_version INTEGER NOT NULL CHECK (question_version >= 1),
    text TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (session_id, question_id, question_version),
    FOREIGN KEY (session_id) REFERENCES sessions (id),
    FOREIGN KEY (question_id, question_version) REFERENCES questions (id, version)
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    status TEXT NOT NULL,
    answer_id TEXT NOT NULL,
    answer_revision INTEGER NOT NULL CHECK (answer_revision >= 1),
    question_id TEXT NOT NULL,
    question_version INTEGER NOT NULL CHECK (question_version >= 1),
    rubric_id TEXT NOT NULL,
    rubric_version INTEGER NOT NULL CHECK (rubric_version >= 1),
    total_score INTEGER,
    maximum_score INTEGER,
    failure_code TEXT,
    failure_message TEXT,
    evaluated_at TEXT,
    prompt_version TEXT,
    model_id TEXT,
    demo_mode_label TEXT,
    PRIMARY KEY (id, version),
    FOREIGN KEY (answer_id, answer_revision) REFERENCES answers (id, revision),
    FOREIGN KEY (question_id, question_version) REFERENCES questions (id, version),
    FOREIGN KEY (rubric_id, rubric_version) REFERENCES rubrics (id, version)
);

CREATE INDEX IF NOT EXISTS idx_evaluations_answer ON evaluations (answer_id, answer_revision);

CREATE TABLE IF NOT EXISTS evaluation_criterion_checks (
    evaluation_id TEXT NOT NULL,
    evaluation_version INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    criterion_id TEXT NOT NULL,
    status TEXT NOT NULL,
    score INTEGER,
    evidence_json TEXT NOT NULL,
    explanation TEXT NOT NULL,
    unresolved_reason TEXT,
    PRIMARY KEY (evaluation_id, evaluation_version, criterion_id),
    FOREIGN KEY (evaluation_id, evaluation_version) REFERENCES evaluations (id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS competency_profiles (
    owner_token_hash TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    criterion_type TEXT NOT NULL,
    observed_count INTEGER NOT NULL CHECK (observed_count >= 1),
    met_count INTEGER NOT NULL CHECK (met_count >= 0),
    unmet_count INTEGER NOT NULL CHECK (unmet_count >= 0),
    unresolved_count INTEGER NOT NULL CHECK (unresolved_count >= 0),
    latest_status TEXT NOT NULL,
    latest_evaluated_at TEXT NOT NULL,
    latest_session_id TEXT NOT NULL,
    latest_answer_id TEXT NOT NULL,
    latest_answer_revision INTEGER NOT NULL CHECK (latest_answer_revision >= 1),
    latest_evaluation_id TEXT NOT NULL,
    latest_evaluation_version INTEGER NOT NULL CHECK (latest_evaluation_version >= 1),
    latest_criterion_id TEXT NOT NULL,
    recent_scored_json TEXT NOT NULL,
    PRIMARY KEY (owner_token_hash, skill_id, criterion_type),
    FOREIGN KEY (skill_id) REFERENCES skills (id),
    FOREIGN KEY (latest_session_id) REFERENCES sessions (id)
);
