from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "src" / "incident_report" / "data"
SEED_SQL = DATA_DIR / "synthetic_cases_seed.sql"
DB_PATH = DATA_DIR / "synthetic_cases.sqlite"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SEED_SQL.read_text(encoding="utf-8"))
        connection.execute("PRAGMA foreign_key_check")
        connection.execute("PRAGMA integrity_check")

    print(f"Wrote {DB_PATH}")


if __name__ == "__main__":
    main()
