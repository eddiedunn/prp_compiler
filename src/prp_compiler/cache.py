import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class ResultCache:
    """Simple SQLite-backed cache for compilation results."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (cache_key TEXT PRIMARY KEY, result_json TEXT, timestamp TEXT)"
        )
        self.conn.commit()

    def get(self, cache_key: str, max_age_hours: int = 24) -> Optional[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT result_json, timestamp FROM cache WHERE cache_key=?", (cache_key,)
        )
        row = cur.fetchone()
        if not row:
            return None
        result_json, timestamp_str = row
        timestamp = datetime.fromisoformat(timestamp_str)
        if datetime.utcnow() - timestamp > timedelta(hours=max_age_hours):
            return None
        return json.loads(result_json)

    def set(self, cache_key: str, result: dict[str, Any]) -> None:
        self.conn.execute(
            "REPLACE INTO cache (cache_key, result_json, timestamp) VALUES (?, ?, ?)",
            (cache_key, json.dumps(result), datetime.utcnow().isoformat()),
        )
        self.conn.commit()
