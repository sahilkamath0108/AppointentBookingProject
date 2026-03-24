import os

from dotenv import load_dotenv

load_dotenv()

from app import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"Starting Appointment Booking server on port {port}")
    print(f"Webhook URL: http://localhost:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=True)
