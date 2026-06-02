from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.settings import DB_PATH


@dataclass
class RunSummary:
    suite_name: str
    module_name: str
    started_at: str
    finished_at: str
    passed: int
    failed: int
    total: int
    status: str
    command: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    sheet_url: str | None = None
    report_path: str | None = None
    browser_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


class ExecutionStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suite_name TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    command TEXT,
                    stdout TEXT,
                    stderr TEXT,
                    sheet_url TEXT,
                    report_path TEXT,
                    browser_breakdown_json TEXT,
                    extra_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS locator_healings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    suite_name TEXT,
                    module_name TEXT,
                    test_name TEXT,
                    locator_name TEXT NOT NULL,
                    previous_selector TEXT,
                    strategy TEXT NOT NULL,
                    chosen_selector TEXT NOT NULL,
                    page_url TEXT,
                    page_title TEXT,
                    html_snapshot TEXT,
                    details_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS step_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    suite_name TEXT,
                    module_name TEXT,
                    test_name TEXT,
                    browser_name TEXT,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    remarks TEXT,
                    screenshot_path TEXT,
                    run_time TEXT,
                    extra_json TEXT
                )
                """
            )
            self._ensure_column(conn, "locator_healings", "previous_selector", "TEXT")
            self._ensure_column(conn, "locator_healings", "html_snapshot", "TEXT")
            self._ensure_column(conn, "locator_healings", "details_json", "TEXT")
            self._ensure_column(conn, "step_events", "remarks", "TEXT")
            self._ensure_column(conn, "step_events", "screenshot_path", "TEXT")
            self._ensure_column(conn, "step_events", "run_time", "TEXT")
            self._ensure_column(conn, "step_events", "extra_json", "TEXT")
            conn.commit()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def record_run(self, summary: RunSummary | dict[str, Any]) -> int:
        payload = asdict(summary) if isinstance(summary, RunSummary) else dict(summary)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO execution_runs (
                    suite_name, module_name, started_at, finished_at, passed, failed, total, status,
                    command, stdout, stderr, sheet_url, report_path, browser_breakdown_json, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["suite_name"],
                    payload["module_name"],
                    payload["started_at"],
                    payload["finished_at"],
                    int(payload["passed"]),
                    int(payload["failed"]),
                    int(payload["total"]),
                    payload["status"],
                    payload.get("command"),
                    payload.get("stdout"),
                    payload.get("stderr"),
                    payload.get("sheet_url"),
                    payload.get("report_path"),
                    json.dumps(payload.get("browser_breakdown", {})),
                    json.dumps(payload.get("extra", {})),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def record_locator_healing(
        self,
        *,
        locator_name: str,
        strategy: str,
        chosen_selector: str,
        suite_name: str | None = None,
        module_name: str | None = None,
        test_name: str | None = None,
        previous_selector: str | None = None,
        page_url: str | None = None,
        page_title: str | None = None,
        html_snapshot: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            self._ensure_column(conn, "locator_healings", "previous_selector", "TEXT")
            self._ensure_column(conn, "locator_healings", "html_snapshot", "TEXT")
            self._ensure_column(conn, "locator_healings", "details_json", "TEXT")
            conn.execute(
                """
                INSERT INTO locator_healings (
                    created_at, suite_name, module_name, test_name, locator_name, previous_selector, strategy,
                    chosen_selector, page_url, page_title, html_snapshot, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    suite_name,
                    module_name,
                    test_name,
                    locator_name,
                    previous_selector,
                    strategy,
                    chosen_selector,
                    page_url,
                    page_title,
                    html_snapshot,
                    json.dumps(details or {}),
                ),
            )
            conn.commit()

    def list_runs(self, limit: int = 50, suite_name: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM execution_runs"
        params: list[Any] = []
        if suite_name:
            query += " WHERE suite_name = ?"
            params.append(suite_name)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def latest_run(self, suite_name: str | None = None) -> dict[str, Any] | None:
        runs = self.list_runs(limit=1, suite_name=suite_name)
        return runs[0] if runs else None

    def list_locator_healings(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM locator_healings ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def record_step_event(
        self,
        *,
        suite_name: str | None,
        module_name: str | None,
        test_name: str | None,
        browser_name: str,
        step_name: str,
        status: str,
        remarks: str | None = None,
        screenshot_path: str | None = None,
        run_time: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO step_events (
                    created_at, suite_name, module_name, test_name, browser_name, step_name, status, remarks,
                    screenshot_path, run_time, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    suite_name,
                    module_name,
                    test_name,
                    browser_name,
                    step_name,
                    status,
                    remarks,
                    screenshot_path,
                    run_time,
                    json.dumps(extra or {}),
                ),
            )
            conn.commit()

    def list_step_events(
        self,
        limit: int = 100,
        suite_name: str | None = None,
        module_name: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM step_events"
        params: list[Any] = []
        clauses: list[str] = []
        if suite_name:
            clauses.append("suite_name = ?")
            params.append(suite_name)
        if module_name:
            clauses.append("module_name = ?")
            params.append(module_name)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        for key in ("browser_breakdown_json", "extra_json", "details_json"):
            if key in payload and payload[key]:
                try:
                    payload[key] = json.loads(payload[key])
                except json.JSONDecodeError:
                    pass
        return payload
