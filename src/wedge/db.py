import json, sqlite3, uuid
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    idea TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    created_at TEXT NOT NULL,
    planner_output_json TEXT,
    candidates_json TEXT,
    competitors_json TEXT,
    complaints_json TEXT,
    brief_json TEXT,
    watched INTEGER NOT NULL DEFAULT 0,
    bright_data_calls INTEGER NOT NULL DEFAULT 0
);
"""

ARTIFACTS = {"planner_output_json", "candidates_json", "competitors_json",
             "complaints_json", "brief_json"}

class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def init_schema(self):
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def create_job(self, *, idea: str) -> str:
        jid = uuid.uuid4().hex[:12]
        self._conn.execute(
            "INSERT INTO jobs (id, idea, created_at) VALUES (?, ?, ?)",
            (jid, idea, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()
        return jid

    def get_job(self, job_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def set_status(self, job_id: str, status: str):
        self._conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        self._conn.commit()

    def save_artifact(self, job_id: str, column: str, value):
        if column not in ARTIFACTS:
            raise ValueError(f"Unknown artifact column: {column}")
        self._conn.execute(f"UPDATE jobs SET {column} = ? WHERE id = ?",
                           (json.dumps(value), job_id))
        self._conn.commit()

    def bump_calls(self, job_id: str, n: int):
        self._conn.execute("UPDATE jobs SET bright_data_calls = bright_data_calls + ? WHERE id = ?",
                           (n, job_id))
        self._conn.commit()

    def set_watched(self, job_id: str, watched: bool):
        self._conn.execute("UPDATE jobs SET watched = ? WHERE id = ?", (1 if watched else 0, job_id))
        self._conn.commit()
