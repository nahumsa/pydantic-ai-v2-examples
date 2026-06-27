from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import StatusEvent, SupportDeskContext, SyntheticCase


DEFAULT_SYNTHETIC_DB = Path(__file__).with_name("data") / "synthetic_cases.sqlite"


def synthetic_case_ids(db_path: Path = DEFAULT_SYNTHETIC_DB) -> tuple[str, ...]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT case_id FROM synthetic_cases ORDER BY case_id"
        ).fetchall()
    return tuple(row["case_id"] for row in rows)


def list_synthetic_cases(db_path: Path = DEFAULT_SYNTHETIC_DB) -> tuple[SyntheticCase, ...]:
    return tuple(get_synthetic_case(case_id, db_path=db_path) for case_id in synthetic_case_ids(db_path))


def get_random_synthetic_case(db_path: Path = DEFAULT_SYNTHETIC_DB) -> SyntheticCase:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT case_id FROM synthetic_cases ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    if row is None:
        raise ValueError("Synthetic case database is empty.")
    return get_synthetic_case(row["case_id"], db_path=db_path)


def get_synthetic_case(case_id: str, db_path: Path = DEFAULT_SYNTHETIC_DB) -> SyntheticCase:
    with _connect(db_path) as connection:
        case_row = connection.execute(
            """
            SELECT
                case_id,
                description,
                prompt,
                customer_name,
                contract_tier,
                customer_region,
                expected_service,
                expected_status,
                expected_email_action
            FROM synthetic_cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()
        if case_row is None:
            known = ", ".join(synthetic_case_ids(db_path))
            raise ValueError(f"Unknown synthetic case {case_id!r}. Known cases: {known}")

        event_rows = connection.execute(
            """
            SELECT service, state, region, minutes_ago, note
            FROM status_events
            WHERE case_id = ?
            ORDER BY sort_order, id
            """,
            (case_id,),
        ).fetchall()

    return SyntheticCase(
        case_id=case_row["case_id"],
        description=case_row["description"],
        prompt=case_row["prompt"],
        context=SupportDeskContext(
            customer_name=case_row["customer_name"],
            contract_tier=case_row["contract_tier"],
            region=case_row["customer_region"],
            status_events=tuple(
                StatusEvent(
                    service=row["service"],
                    state=row["state"],
                    region=row["region"],
                    minutes_ago=row["minutes_ago"],
                    note=row["note"],
                )
                for row in event_rows
            ),
        ),
        expected_service=case_row["expected_service"],
        expected_status=case_row["expected_status"],
        expected_email_action=case_row["expected_email_action"],
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Synthetic case database not found at {db_path}. "
            "Run `uv run python scripts/build_synthetic_db.py` to create it."
        )
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection
