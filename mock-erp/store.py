"""Durable demo ERP. Every capacity decision uses an SQLite write transaction."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

KINDS = (
    "hospitals",
    "specialties",
    "departments",
    "doctors",
    "appointment_types",
    "slots",
    "bookings",
)


@contextmanager
def transaction():
    path = Path(os.getenv("ERP_DB_PATH", "/tmp/carebook-erp.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id))"
        )
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def rows(db, kind):
    return [
        json.loads(row[0])
        for row in db.execute(
            "SELECT body FROM records WHERE kind=? ORDER BY id", (kind,)
        )
    ]


def get(db, kind, identifier):
    row = db.execute(
        "SELECT body FROM records WHERE kind=? AND id=?", (kind, identifier)
    ).fetchone()
    return json.loads(row[0]) if row else None


def put(db, kind, identifier, body):
    db.execute(
        "INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
        (kind, identifier, json.dumps(body)),
    )
