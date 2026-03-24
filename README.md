# Dental Scheduling Assistant

Multi-agent service for managing dental appointments with LangGraph and Grok-4 (xAI).  
Supports both CLI chat and WhatsApp chat via Twilio, backed by SQLite storage.

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
- SQLite (`sqlite3`) for persistence and CRUD operations
- Pydantic for structured routing output

## Project Layout

```
AppointentBookingProject/
├── main.py
├── app.py                           # Flask API + Twilio webhook
├── run.py                           # Server launcher
├── appointments.db                 # Generated on first run
├── doctor_availability.csv         # Optional bootstrap source (legacy)
├── requirements.txt
├── services/
│   └── twilio_service.py
└── dental_agent/
    ├── agent.py
    ├── config/settings.py
    ├── models/state.py
    ├── workflows/graph.py
    ├── tools/
    │   ├── db_reader.py
    │   └── db_writer.py
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
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
PORT=5000
```

## Run

### CLI mode
```bash
python main.py
```

### WhatsApp / API mode
```bash
python run.py
```

Webhook endpoint for Twilio:
- `POST /webhook`

Direct test endpoint:
- `POST /api/chat` with JSON body:
  - `message` (required)
  - `user_id` (optional)

Example:
```bash
curl -X POST http://localhost:5000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"show available slots for orthodontist\",\"user_id\":\"demo\"}"
```

Health check:
- `GET /health`

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

## Schedule Data Model

Primary data source: `appointments.db` (`appointments` table)

| Field | Description |
|-------|-------------|
| `date_slot` | Appointment date and time |
| `specialization` | Provider specialization |
| `doctor_name` | Provider full name |
| `is_available` | Slot availability (`TRUE` / `FALSE`) |
| `patient_to_attend` | Patient ID for booked slots |

On first run, the application bootstraps the `appointments` table from `doctor_availability.csv` if the database is empty.
