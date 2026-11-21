"""Atomic request reservations shared by the live providers."""
from pathlib import Path
import sqlite3
from threading import Lock
from source.Model.repositories.interfaces import RepositoryError


class RequestBudget:
    def __init__(self, limit: int, path: Path | None):
        self.limit = limit
        self._budget_path = path
        self._used = 0
        self._lock = Lock()

    def reserve(self) -> bool:
        try:
            return self._reserve()
        except (sqlite3.Error, OSError) as error:
            raise RepositoryError("Cannot reserve request budget.") from error

    def _reserve(self) -> bool:
        if self._budget_path is None:
            with self._lock:
                if self._used < self.limit:
                    self._used += 1
                    return True
        else:
            # Atomic reservation across processes, including retries and restarts.
            self._budget_path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self._budget_path)
            try:
                with db:
                    db.execute("CREATE TABLE IF NOT EXISTS gemini_budget (id INTEGER PRIMARY KEY, used INTEGER NOT NULL)")
                    db.execute("INSERT OR IGNORE INTO gemini_budget VALUES (1, 0)")
                    updated = db.execute("UPDATE gemini_budget SET used=used+1 WHERE id=1 AND used < ?",
                                         (self.limit,))
                    if updated.rowcount:
                        return True
            finally:
                db.close()
        return False
