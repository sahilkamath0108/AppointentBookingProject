import pandas as pd
from langchain_core.tools import tool
from dental_agent.config.settings import CSV_PATH


def _load_df() -> pd.DataFrame:
    schedule_frame = pd.read_csv(CSV_PATH)
    schedule_frame.columns = schedule_frame.columns.str.strip()
    schedule_frame["is_available"] = schedule_frame["is_available"].astype(str).str.upper() == "TRUE"
    schedule_frame["date_slot"] = pd.to_datetime(schedule_frame["date_slot"], format="mixed", dayfirst=False)
    schedule_frame["doctor_name"] = schedule_frame["doctor_name"].str.lower().str.strip()
    schedule_frame["specialization"] = schedule_frame["specialization"].str.lower().str.strip()
    schedule_frame["patient_to_attend"] = (
        schedule_frame["patient_to_attend"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)  # 1000082.0 → 1000082
    )
    return schedule_frame


def _save_df(schedule_frame: pd.DataFrame) -> None:
    output_frame = schedule_frame.copy()
    output_frame["date_slot"] = output_frame["date_slot"].dt.strftime("%-m/%-d/%Y %-H:%M")
    output_frame["is_available"] = output_frame["is_available"].map({True: "TRUE", False: "FALSE"})
    output_frame["patient_to_attend"] = (
        output_frame["patient_to_attend"]
        .replace("nan", "")
        .str.replace(r"\.0$", "", regex=True)
    )
    output_frame.to_csv(CSV_PATH, index=False)


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
    schedule_frame = _load_df()
    try:
        target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doc = doctor_name.lower().strip()
    filter_mask = (schedule_frame["doctor_name"] == doc) & (schedule_frame["date_slot"] == target_dt)
    rows = schedule_frame[filter_mask]

    if rows.empty:
        return {"success": False, "message": "Slot not found for this doctor."}
    if not rows.iloc[0]["is_available"]:
        return {"success": False, "message": "Slot is already booked."}

    schedule_frame.loc[filter_mask, "is_available"] = False
    schedule_frame.loc[filter_mask, "patient_to_attend"] = str(patient_id).strip()
    _save_df(schedule_frame)
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
    schedule_frame = _load_df()
    try:
        target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    pid = str(patient_id).strip()
    filter_mask = (
        (schedule_frame["patient_to_attend"] == pid)
        & (schedule_frame["date_slot"] == target_dt)
        & (~schedule_frame["is_available"])
    )
    rows = schedule_frame[filter_mask]

    if rows.empty:
        return {
            "success": False,
            "message": f"No booked appointment found for patient {patient_id} at {date_slot}.",
        }

    schedule_frame.loc[filter_mask, "is_available"] = True
    schedule_frame.loc[filter_mask, "patient_to_attend"] = ""
    _save_df(schedule_frame)
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
    schedule_frame = _load_df()
    try:
        current_dt = pd.to_datetime(current_date_slot, format="mixed", dayfirst=False)
        new_dt = pd.to_datetime(new_date_slot, format="mixed", dayfirst=False)
    except Exception as exc:
        return {"success": False, "message": f"Date parse error: {exc}"}

    doc = doctor_name.lower().strip()
    pid = str(patient_id).strip()

    old_slot_mask = (
        (schedule_frame["patient_to_attend"] == pid)
        & (schedule_frame["date_slot"] == current_dt)
        & (~schedule_frame["is_available"])
    )
    if schedule_frame[old_slot_mask].empty:
        return {
            "success": False,
            "message": f"No existing booking found for patient {pid} at {current_date_slot}.",
        }

    new_slot_mask = (schedule_frame["doctor_name"] == doc) & (schedule_frame["date_slot"] == new_dt)
    new_rows = schedule_frame[new_slot_mask]
    if new_rows.empty:
        return {"success": False, "message": f"Slot {new_date_slot} does not exist for {doctor_name}."}
    if not new_rows.iloc[0]["is_available"]:
        return {"success": False, "message": f"Slot {new_date_slot} is already taken."}

    schedule_frame.loc[old_slot_mask, "is_available"] = True
    schedule_frame.loc[old_slot_mask, "patient_to_attend"] = ""
    schedule_frame.loc[new_slot_mask, "is_available"] = False
    schedule_frame.loc[new_slot_mask, "patient_to_attend"] = pid
    _save_df(schedule_frame)
    return {
        "success": True,
        "message": (
            f"Appointment for patient {pid} rescheduled from "
            f"{current_date_slot} to {new_date_slot} with {doctor_name}."
        ),
    }
