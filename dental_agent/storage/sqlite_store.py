import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dental_agent.config.settings import DB_PATH, LEGACY_CSV_PATH


def _normalize_bool(raw_value: str) -> int:
    return 1 if str(raw_value).strip().upper() == "TRUE" else 0


def normalize_slot_for_db(raw_slot: str) -> Optional[str]:
    """Parse multiple input formats and persist as ISO-like sqlite text."""
    if raw_slot is None:
        return None

    slot_text = str(raw_slot).strip()
    if not slot_text:
        return None

    candidate_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %H:%M",
        "%m/%d/%y %H:%M",
        "%m-%d-%Y %H:%M",
    )

    parsed = None
    for fmt in candidate_formats:
        try:
            parsed = datetime.strptime(slot_text, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        try:
            parsed = datetime.fromisoformat(slot_text.replace("T", " "))
        except ValueError:
            return None

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_slot_for_user(db_slot: str) -> str:
    parsed = datetime.strptime(db_slot, "%Y-%m-%d %H:%M:%S")
    return f"{parsed.month}/{parsed.day}/{parsed.year} {parsed.hour}:{parsed.minute:02d}"


def _bootstrap_from_csv(conn: sqlite3.Connection) -> None:
    csv_path = Path(LEGACY_CSV_PATH)
    if not csv_path.exists():
        return

    with conn:
        cursor = conn.execute("SELECT COUNT(*) FROM appointments")
        existing_rows = cursor.fetchone()[0]
        if existing_rows > 0:
            return

        with csv_path.open("r", encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            rows = []
            for row in reader:
                normalized_slot = normalize_slot_for_db(row.get("date_slot", ""))
                if normalized_slot is None:
                    continue
                rows.append(
                    (
                        normalized_slot,
                        str(row.get("specialization", "")).strip().lower(),
                        str(row.get("doctor_name", "")).strip().lower(),
                        _normalize_bool(row.get("is_available", "")),
                        str(row.get("patient_to_attend", "")).strip(),
                    )
                )

            conn.executemany(
                """
                INSERT OR IGNORE INTO appointments (
                    date_slot, specialization, doctor_name, is_available, patient_to_attend
                ) VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_slot TEXT NOT NULL,
            specialization TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            is_available INTEGER NOT NULL CHECK (is_available IN (0, 1)),
            patient_to_attend TEXT,
            UNIQUE (doctor_name, date_slot)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_available ON appointments(is_available)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_to_attend)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_specialization ON appointments(specialization)")
    conn.commit()

    _bootstrap_from_csv(conn)
    return conn
