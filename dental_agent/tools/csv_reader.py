import pandas as pd
from langchain_core.tools import tool
from dental_agent.config.settings import CSV_PATH, DATE_FORMAT


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
    schedule_frame = _load_df()
    filter_mask = schedule_frame["is_available"]

    if specialization:
        filter_mask = filter_mask & (schedule_frame["specialization"] == specialization.lower().strip())
    if doctor_name:
        filter_mask = filter_mask & (schedule_frame["doctor_name"] == doctor_name.lower().strip())
    if date_filter:
        try:
            target_date = pd.to_datetime(date_filter).date()
            filter_mask = filter_mask & (schedule_frame["date_slot"].dt.date == target_date)
        except Exception:
            pass

    result = schedule_frame[filter_mask][["date_slot", "specialization", "doctor_name"]].copy()
    result["date_slot"] = result["date_slot"].dt.strftime("%-m/%-d/%Y %-H:%M")
    return result.head(20).to_dict(orient="records")


@tool
def get_patient_appointments(patient_id: str) -> list:
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """
    schedule_frame = _load_df()
    filter_mask = schedule_frame["patient_to_attend"] == str(patient_id).strip()
    result = schedule_frame[filter_mask][["date_slot", "specialization", "doctor_name", "patient_to_attend"]].copy()
    result["date_slot"] = result["date_slot"].dt.strftime("%-m/%-d/%Y %-H:%M")
    return result.to_dict(orient="records")


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
    schedule_frame = _load_df()
    try:
        target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
    except Exception:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    filter_mask = (schedule_frame["doctor_name"] == doctor_name.lower().strip()) & (schedule_frame["date_slot"] == target_dt)
    rows = schedule_frame[filter_mask]

    if rows.empty:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    row = rows.iloc[0]
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
    schedule_frame = _load_df()
    filter_mask = schedule_frame["specialization"] == specialization.lower().strip()
    return sorted(schedule_frame[filter_mask]["doctor_name"].unique().tolist())
