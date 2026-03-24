import os
import secrets
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from langchain_core.messages import BaseMessage

from dental_agent.chat_session import run_chat_turn
from services.twilio_service import TwilioService

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))

twilio_service = TwilioService()
user_sessions: dict[str, list[BaseMessage]] = {}


def _ensure_session(user_id: str) -> None:
    if user_id not in user_sessions:
        user_sessions[user_id] = []


def _process_message_background(sender: str, incoming_text: str) -> None:
    try:
        _ensure_session(sender)
        response_text, updated_history = run_chat_turn(user_sessions[sender], incoming_text)
        user_sessions[sender] = updated_history
        twilio_service.send_message(sender, response_text or "I could not generate a response.")
    except Exception:
        # Keep webhook resilient; errors can be inspected through server logs.
        pass


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_text = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if not incoming_text or not sender:
        return twilio_service.create_response(
            "Error: missing message or sender metadata in webhook payload."
        )

    threading.Thread(
        target=_process_message_background,
        args=(sender, incoming_text),
        daemon=True,
    ).start()

    return twilio_service.create_response(
        "Message received. I am processing your appointment request now."
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json() or {}
    message = str(payload.get("message", "")).strip()
    user_id = str(payload.get("user_id", "api_user")).strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    _ensure_session(user_id)
    response_text, updated_history = run_chat_turn(user_sessions[user_id], message)
    user_sessions[user_id] = updated_history

    return jsonify(
        {
            "response": response_text,
            "user_id": user_id,
            "history_length": len(updated_history),
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": "appointment-booking-whatsapp",
            "twilio_client_ready": bool(twilio_service.client),
        }
    )


@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "message": "Appointment Booking API is running",
            "endpoints": {
                "webhook": "/webhook (POST) - Twilio WhatsApp webhook",
                "api_chat": "/api/chat (POST) - direct testing endpoint",
                "health": "/health (GET) - service health",
            },
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
