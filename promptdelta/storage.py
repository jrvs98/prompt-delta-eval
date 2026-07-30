from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment TEXT NOT NULL,
    model_label TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    task_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    condition TEXT NOT NULL,
    run_index INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    output TEXT NOT NULL,
    score REAL,
    eval_details TEXT,
    format_ok INTEGER,
    format_details TEXT,
    latency_ms INTEGER,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_results_group
    ON results (experiment, model_label, task_id, condition);
"""


def init_db(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def save_result(db_path: str | Path, row: Dict[str, Any]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO results (
                experiment, model_label, provider, model, task_id, item_id,
                condition, run_index, prompt, output, score, eval_details,
                format_ok, format_details, latency_ms, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["experiment"],
                row["model_label"],
                row["provider"],
                row["model"],
                row["task_id"],
                row["item_id"],
                row["condition"],
                row["run_index"],
                row["prompt"],
                row["output"],
                row.get("score"),
                json.dumps(row.get("eval_details", {})),
                int(bool(row.get("format_ok"))) if row.get("format_ok") is not None else None,
                json.dumps(row.get("format_details", {})),
                row.get("latency_ms"),
                row.get("error"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_all(db_path: str | Path, experiment: str | None = None) -> Iterable[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if experiment:
            cur = conn.execute("SELECT * FROM results WHERE experiment = ?", (experiment,))
        else:
            cur = conn.execute("SELECT * FROM results")
        return cur.fetchall()
    finally:
        conn.close()
