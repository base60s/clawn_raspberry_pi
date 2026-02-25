from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: int
    kind: str
    status: str
    payload: dict[str, Any]
    attempts: int = 0
    max_attempts: int = 3
    created_at: str = ""
    updated_at: str = ""
    result_json: str | None = None
    error: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Job":
        return cls(
            id=row["id"],
            kind=row["kind"],
            status=row["status"],
            payload=json.loads(row["payload"]),
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            result_json=row["result_json"],
            error=row["error"],
        )


class QueueManager:
    def __init__(self, path: str = ".saferclaw.jobs.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path.as_posix(), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self.conn.close()

    def _ensure_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT
                )
                """
            )
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_updated ON jobs(updated_at)")

    def enqueue(self, kind: str, payload: dict[str, Any], max_attempts: int = 3) -> int:
        now = _utcnow_iso()
        serialized = json.dumps(payload)
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO jobs(kind, status, payload, attempts, max_attempts, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (kind, "queued", serialized, max_attempts, now, now),
            )
        return int(cursor.lastrowid)

    def claim_next(self) -> Job | None:
        # SQLite doesn't support skip-locked on all versions, so we use a small transaction
        # with a direct status update to claim one queued row.
        with self.conn:
            row = self.conn.execute(
                """
                SELECT id FROM jobs
                WHERE status = "queued"
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            now = _utcnow_iso()
            self.conn.execute(
                """
                UPDATE jobs
                SET status = "running", updated_at = ?, attempts = attempts + 1
                WHERE id = ?
                """,
                (now, row["id"]),
            )
            job_row = self.conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (row["id"],),
            ).fetchone()
            return Job.from_row(job_row)

    def mark_done(self, job_id: int, result_json: str) -> None:
        with self.conn:
            self.conn.execute(
                """
                UPDATE jobs
                SET status = "done", updated_at = ?, result_json = ?, error = NULL
                WHERE id = ?
                """,
                (_utcnow_iso(), result_json, job_id),
            )

    def mark_failed(self, job_id: int, error: str, retryable: bool = True) -> None:
        row = self.conn.execute(
            "SELECT attempts, max_attempts FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return
        status = "queued" if (retryable and row["attempts"] < row["max_attempts"]) else "failed"
        with self.conn:
            self.conn.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, error = ?
                WHERE id = ?
                """,
                (status, _utcnow_iso(), error, job_id),
            )

    def mark_blocked(self, job_id: int, reason: str) -> None:
        with self.conn:
            self.conn.execute(
                """
                UPDATE jobs
                SET status = "blocked", updated_at = ?, error = ?
                WHERE id = ?
                """,
                (_utcnow_iso(), reason, job_id),
            )

    def list_jobs(self, status: str | None = None, limit: int = 50) -> list[Job]:
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [Job.from_row(row) for row in rows]

