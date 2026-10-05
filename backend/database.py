"""Small, persistent job store. One local API process owns the worker queue."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .settings import RUNTIME


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(RUNTIME / "geodyssey.sqlite3", timeout=30) as db:
        db.row_factory = sqlite3.Row
        yield db


def initialize(recover=True):
    with connection() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, finished_at TEXT,
            status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
            stage TEXT NOT NULL, parameters TEXT NOT NULL, error TEXT,
            summary TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY, metadata TEXT NOT NULL, checked_at TEXT NOT NULL)""")
        if recover:
            db.execute("""UPDATE runs SET status='failed', error='Application stopped before this run finished.',
                stage='Interrupted', finished_at=? WHERE status IN ('queued','running')""", (now(),))
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs((1)) WHERE status IN ('queued','running')")


def unpack(row):
    if row is None:
        return None
    result = dict(row)
    for key in ("parameters", "summary"):
        result[key] = json.loads(result[key]) if result[key] else None
    return result


def create_run(run_id, parameters):
    with connection() as db:
        db.execute("INSERT INTO runs(id,created_at,status,stage,parameters) VALUES(?,?,'queued','Queued',?)",
                   (run_id, now(), json.dumps(parameters)))


def update_run(run_id, **fields):
    allowed = {"status", "stage", "progress", "finished_at", "error", "summary"}
    if not fields or not set(fields) <= allowed:
        raise ValueError("Invalid job update")
    if "summary" in fields:
        fields["summary"] = json.dumps(fields["summary"], allow_nan=False)
    with connection() as db:
        db.execute(f"UPDATE runs SET {','.join(k+'=?' for k in fields)} WHERE id=?",
                   (*fields.values(), run_id))


def get_run(run_id):
    with connection() as db:
        return unpack(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())


def list_runs():
    with connection() as db:
        return [unpack(row) for row in db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 100")]


def save_datasets(datasets):
    with connection() as db:
        db.executemany("INSERT OR REPLACE INTO datasets VALUES(?,?,?)",
                       [(item["id"], json.dumps(item), now()) for item in datasets])
