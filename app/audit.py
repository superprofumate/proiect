import json
import sqlite3
from datetime import datetime, timezone

class Audit:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS audit (request_id TEXT PRIMARY KEY, at TEXT, status TEXT, decision TEXT)')

    def record(self, request_id, status, decision=None):
        # No prompts, raw records, credentials or upstream error messages.
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO audit VALUES (?, ?, ?, ?)',
                       (request_id, datetime.now(timezone.utc).isoformat(), status,
                        json.dumps(decision.model_dump()) if decision else None))
