# Dental Scheduling Assistant

Multi-agent CLI service for managing dental appointments with LangGraph and Grok-4 (xAI).  
The assistant handles discovery, booking, cancellation, and rescheduling against a CSV schedule store.

## Capabilities

- Check open slots by specialization, provider name, and date
- List appointments for a specific patient ID
- Book a new appointment after availability validation
- Cancel an existing appointment with explicit confirmation
- Move an existing booking to a new valid slot

## Runtime Architecture

The application uses a routing node and focused specialist agents:

- `supervisor`: classifies intent and routes to the next agent
- `info_agent`: read-only questions about slots, providers, and patient bookings
- `booking_agent`: creates new appointments
- `cancellation_agent`: cancels existing appointments
- `rescheduling_agent`: relocates existing bookings

Graph execution is defined in `dental_agent/workflows/graph.py` using LangGraph conditional edges.

## Stack

- LangGraph and LangChain
- xAI Grok-4 via `langchain-xai`
- Pandas for CSV persistence and filtering
- Pydantic for structured routing output

## Project Layout

```
AppointentBookingProject/
├── main.py
├── doctor_availability.csv
├── requirements.txt
└── dental_agent/
    ├── agent.py
    ├── config/settings.py
    ├── models/state.py
    ├── workflows/graph.py
    ├── tools/
    │   ├── csv_reader.py
    │   └── csv_writer.py
    └── agents/
        ├── supervisor.py
        ├── info_agent.py
        ├── booking_agent.py
        ├── cancellation_agent.py
        └── rescheduling_agent.py
```

## Setup

### Prerequisites

- Python 3.10+
- xAI API key with access to Grok-4

### Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment

Create `.env` in the project root:

```env
XAI_API_KEY=your_api_key_here
MODEL_NAME=grok-4
TEMPERATURE=0
```

## Run

```bash
python main.py
```

## Input Conventions

- Date format: `M/D/YYYY H:MM` (example: `5/10/2026 9:00`)
- Specialization values:
  - `general_dentist`
  - `oral_surgeon`
  - `orthodontist`
  - `cosmetic_dentist`
  - `prosthodontist`
  - `pediatric_dentist`
  - `emergency_dentist`

## Schedule Dataset

Data source: `doctor_availability.csv`

| Field | Description |
|-------|-------------|
| `date_slot` | Appointment date and time |
| `specialization` | Provider specialization |
| `doctor_name` | Provider full name |
| `is_available` | Slot availability (`TRUE` / `FALSE`) |
| `patient_to_attend` | Patient ID for booked slots |
