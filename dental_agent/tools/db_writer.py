from langchain_core.tools import tool
from dental_agent.storage.sqlite_store import get_connection, normalize_slot_for_db


@tool
def book_appointment(patient_id: str, doctor_name: str, date_slot: str) -> dict:
    """
    Book an appointment: mark slot as unavailable and assign patient_id.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.
        doctor_name: Doctor name (case-insensitive), e.g. 'emily johnson'.
        date_slot: Slot in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    target_slot = normalize_slot_for_db(date_slot)
    if target_slot is None:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doctor_key = doctor_name.lower().strip()
    patient_key = str(patient_id).strip()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT is_available
            FROM appointments
            WHERE doctor_name = ? AND date_slot = ?
            LIMIT 1
            """,
            (doctor_key, target_slot),
        ).fetchone()
        if row is None:
            return {"success": False, "message": "Slot not found for this doctor."}
        if int(row["is_available"]) == 0:
            return {"success": False, "message": "Slot is already booked."}

        conn.execute(
            """
            UPDATE appointments
            SET is_available = 0, patient_to_attend = ?
            WHERE doctor_name = ? AND date_slot = ? AND is_available = 1
            """,
            (patient_key, doctor_key, target_slot),
        )
        conn.commit()

    return {
        "success": True,
        "message": f"Appointment booked for patient {patient_id} with {doctor_name} at {date_slot}.",
    }


@tool
def cancel_appointment(patient_id: str, date_slot: str) -> dict:
    """
    Cancel an appointment: mark slot available and clear patient_id.

    Args:
        patient_id: Patient whose appointment to cancel.
        date_slot: Slot in M/D/YYYY H:MM format to cancel.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    target_slot = normalize_slot_for_db(date_slot)
    if target_slot is None:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    patient_key = str(patient_id).strip()
    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE appointments
            SET is_available = 1, patient_to_attend = ''
            WHERE patient_to_attend = ? AND date_slot = ? AND is_available = 0
            """,
            (patient_key, target_slot),
        )
        conn.commit()
        if result.rowcount == 0:
            return {
                "success": False,
                "message": f"No booked appointment found for patient {patient_id} at {date_slot}.",
            }

    return {
        "success": True,
        "message": f"Appointment at {date_slot} for patient {patient_id} has been cancelled.",
    }


@tool
def reschedule_appointment(
    patient_id: str,
    current_date_slot: str,
    new_date_slot: str,
    doctor_name: str,
) -> dict:
    """
    Reschedule by cancelling the old slot and booking a new one atomically.

    Args:
        patient_id: Patient whose appointment to reschedule.
        current_date_slot: Existing booked slot to vacate (M/D/YYYY H:MM).
        new_date_slot: Desired new slot (M/D/YYYY H:MM).
        doctor_name: Doctor name (must match the booking's doctor).

    Returns:
        Dict with keys: success (bool), message (str).
    """
    current_slot = normalize_slot_for_db(current_date_slot)
    new_slot = normalize_slot_for_db(new_date_slot)
    if current_slot is None or new_slot is None:
        return {"success": False, "message": "Date parse error: Invalid slot format."}

    doctor_key = doctor_name.lower().strip()
    patient_key = str(patient_id).strip()

    with get_connection() as conn:
        existing_booking = conn.execute(
            """
            SELECT id
            FROM appointments
            WHERE patient_to_attend = ? AND date_slot = ? AND is_available = 0
            LIMIT 1
            """,
            (patient_key, current_slot),
        ).fetchone()
        if existing_booking is None:
            return {
                "success": False,
                "message": f"No existing booking found for patient {patient_key} at {current_date_slot}.",
            }

        target_slot = conn.execute(
            """
            SELECT is_available
            FROM appointments
            WHERE doctor_name = ? AND date_slot = ?
            LIMIT 1
            """,
            (doctor_key, new_slot),
        ).fetchone()
        if target_slot is None:
            return {"success": False, "message": f"Slot {new_date_slot} does not exist for {doctor_name}."}
        if int(target_slot["is_available"]) == 0:
            return {"success": False, "message": f"Slot {new_date_slot} is already taken."}

        conn.execute(
            """
            UPDATE appointments
            SET is_available = 1, patient_to_attend = ''
            WHERE patient_to_attend = ? AND date_slot = ? AND is_available = 0
            """,
            (patient_key, current_slot),
        )
        conn.execute(
            """
            UPDATE appointments
            SET is_available = 0, patient_to_attend = ?
            WHERE doctor_name = ? AND date_slot = ? AND is_available = 1
            """,
            (patient_key, doctor_key, new_slot),
        )
        conn.commit()

    return {
        "success": True,
        "message": (
            f"Appointment for patient {patient_key} rescheduled from "
            f"{current_date_slot} to {new_date_slot} with {doctor_name}."
        ),
    }
