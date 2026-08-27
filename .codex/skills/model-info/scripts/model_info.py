#!/usr/bin/env python3
"""Report the effective model metadata for the current Codex thread."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote


def _codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _state_databases(codex_home: Path) -> list[Path]:
    """Return plausible state databases, newest first."""
    candidates = {
        path
        for pattern in (
            "state.sqlite",
            "state_*.sqlite",
            "state.sqlite3",
            "state_*.sqlite3",
        )
        for path in codex_home.glob(pattern)
        if path.is_file()
    }
    return sorted(candidates, key=lambda path: path.stat().st_mtime_ns, reverse=True)


def _read_thread(database: Path, thread_id: str) -> dict[str, str] | None:
    """Read one thread row without taking a write lock on the state DB."""
    database_uri = f"file:{quote(str(database), safe='/')}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True)
    except sqlite3.Error:
        return None

    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'threads'"
        ).fetchone()
        if table is None:
            return None

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(threads)")
        }
        required = {"id", "model", "reasoning_effort"}
        if not required.issubset(columns):
            return None

        selected_columns = ["id", "model", "reasoning_effort"]
        if "model_provider" in columns:
            selected_columns.insert(1, "model_provider")
        row = connection.execute(
            f"SELECT {', '.join(selected_columns)} FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None

        result = dict(
            zip(
                selected_columns,
                ("" if value is None else str(value) for value in row),
            )
        )
        if not result["model"] or not result["reasoning_effort"]:
            return None
        return result
    except sqlite3.Error:
        return None
    finally:
        connection.close()


def _result(thread_id: str, codex_home: Path) -> dict[str, str]:
    databases = _state_databases(codex_home)
    if not databases:
        raise RuntimeError(f"no Codex state database found under {codex_home}")

    for database in databases:
        row = _read_thread(database, thread_id)
        if row is not None:
            row["thread_id"] = thread_id
            row["database"] = str(database)
            return row

    raise RuntimeError(
        f"thread {thread_id} was not found in Codex state databases under {codex_home}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report the effective model and reasoning effort for a Codex thread."
    )
    parser.add_argument(
        "--thread-id",
        help="Thread ID to inspect; defaults to CODEX_THREAD_ID.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    args = parser.parse_args()

    thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
    if not thread_id:
        message = "CODEX_THREAD_ID is not set; cannot identify the active Codex thread"
        if args.json:
            print(json.dumps({"status": "unavailable", "reason": message}))
        else:
            print(f"unavailable: {message}")
        return 1

    try:
        result = _result(thread_id, _codex_home())
    except RuntimeError as error:
        if args.json:
            print(json.dumps({"status": "unavailable", "reason": str(error)}))
        else:
            print(f"unavailable: {error}")
        return 1

    result["status"] = "ok"
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"model: {result['model']}")
        print(f"reasoning_effort: {result['reasoning_effort']}")
        if result.get("model_provider"):
            print(f"provider: {result['model_provider']}")
        print(f"thread_id: {result['thread_id']}")
        print(f"database: {result['database']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
