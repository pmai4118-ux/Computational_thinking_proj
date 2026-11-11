import sqlite3
from contextlib import contextmanager
from pathlib import Path

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport


class SqliteSubmissionRepository:
    def __init__(self, databasePath: Path):
        self.databasePath = databasePath
        databasePath.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS submissions (answerId TEXT, revision INTEGER, inputHash TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(answerId, revision))")
            connection.execute("CREATE TABLE IF NOT EXISTS reports (inputHash TEXT, runKey TEXT, payload TEXT NOT NULL, PRIMARY KEY(inputHash, runKey), FOREIGN KEY(inputHash) REFERENCES submissions(inputHash))")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.databasePath, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def saveInput(self, inputs: EvaluationInput) -> None:
        with self.connect() as connection:
            row = connection.execute("SELECT inputHash FROM submissions WHERE answerId=? AND revision=?", (inputs.answer.answerId, inputs.answer.revision)).fetchone()
            if row and row[0] != inputs.inputDigest():
                raise ValueError("This answer revision already belongs to different input.")
            connection.execute("INSERT OR IGNORE INTO submissions VALUES (?, ?, ?, ?)", (inputs.answer.answerId, inputs.answer.revision, inputs.inputDigest(), inputs.model_dump_json()))

    def loadReport(self, inputHash: str, runKey: str) -> EvaluationReport | None:
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM reports WHERE inputHash=? AND runKey=?", (inputHash, runKey)).fetchone()
        if row is None:
            return None
        report = EvaluationReport.model_validate_json(row[0])
        if report.inputHash != inputHash or report.inputs.inputDigest() != inputHash:
            raise ValueError("The stored report does not match its input.")
        return report

    def saveReport(self, report: EvaluationReport, runKey: str) -> None:
        with self.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO reports VALUES (?, ?, ?)", (report.inputHash, runKey, report.model_dump_json()))

    def findReports(self, inputHash: str) -> list[EvaluationReport]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM reports WHERE inputHash=?", (inputHash,)).fetchall()
        return [EvaluationReport.model_validate_json(row[0]) for row in rows]
