from langchain_core.tools import tool
from dental_agent.storage.sqlite_store import format_slot_for_user, get_connection, normalize_slot_for_db


@tool
def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list:
    """
    Return available (is_available=TRUE) appointment slots.

    Args:
        specialization: Filter by specialization, e.g. 'orthodontist'. Leave empty to skip.
        doctor_name: Filter by doctor name (case-insensitive), e.g. 'emily johnson'. Leave empty to skip.
        date_filter: Filter by date string M/D/YYYY, e.g. '5/10/2026'. Leave empty to skip.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name.
        Returns at most 20 rows to keep response concise.
    """
    clauses = ["is_available = 1"]
    params = []

    if specialization:
        clauses.append("specialization = ?")
        params.append(specialization.lower().strip())
    if doctor_name:
        clauses.append("doctor_name = ?")
        params.append(doctor_name.lower().strip())
    if date_filter:
        parsed_date = normalize_slot_for_db(f"{date_filter.strip()} 00:00")
        if parsed_date:
            clauses.append("date(date_slot) = date(?)")
            params.append(parsed_date[:10])

    query = f"""
        SELECT date_slot, specialization, doctor_name
        FROM appointments
        WHERE {" AND ".join(clauses)}
        ORDER BY datetime(date_slot) ASC
        LIMIT 20
    """
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "date_slot": format_slot_for_user(row["date_slot"]),
            "specialization": row["specialization"],
            "doctor_name": row["doctor_name"],
        }
        for row in rows
    ]


@tool
def get_patient_appointments(patient_id: str) -> list:
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """
    patient_key = str(patient_id).strip()
    query = """
        SELECT date_slot, specialization, doctor_name, patient_to_attend
        FROM appointments
        WHERE patient_to_attend = ? AND is_available = 0
        ORDER BY datetime(date_slot) ASC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (patient_key,)).fetchall()

    return [
        {
            "date_slot": format_slot_for_user(row["date_slot"]),
            "specialization": row["specialization"],
            "doctor_name": row["doctor_name"],
            "patient_to_attend": row["patient_to_attend"],
        }
        for row in rows
    ]


@tool
def check_slot_availability(doctor_name: str, date_slot: str) -> dict:
    """
    Check if a specific doctor slot is available.

    Args:
        doctor_name: Doctor name, e.g. 'emily johnson'.
        date_slot: Slot string in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: found (bool), is_available (bool), patient_to_attend (str).
    """
    normalized_slot = normalize_slot_for_db(date_slot)
    if normalized_slot is None:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT is_available, patient_to_attend
            FROM appointments
            WHERE doctor_name = ? AND date_slot = ?
            LIMIT 1
            """,
            (doctor_name.lower().strip(), normalized_slot),
        ).fetchone()

    if row is None:
        return {"found": False, "is_available": False, "patient_to_attend": ""}
    return {
        "found": True,
        "is_available": bool(row["is_available"]),
        "patient_to_attend": row["patient_to_attend"],
    }


@tool
def list_doctors_by_specialization(specialization: str) -> list:
    """
    Return distinct doctor names for a given specialization.

    Args:
        specialization: e.g. 'orthodontist'.

    Returns:
        Sorted list of doctor name strings.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT doctor_name
            FROM appointments
            WHERE specialization = ?
            ORDER BY doctor_name ASC
            """,
            (specialization.lower().strip(),),
        ).fetchall()
    return [row["doctor_name"] for row in rows]
