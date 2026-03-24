import os

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse


class TwilioService:
    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.client = (
            Client(self.account_sid, self.auth_token)
            if self.account_sid and self.auth_token
            else None
        )

    def create_response(self, message: str) -> str:
        response = MessagingResponse()
        response.message(message)
        return str(response)

    def send_message(self, to: str, message: str) -> str:
        if not self.client:
            raise ValueError(
                "Twilio client is not initialized. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
            )

        twilio_message = self.client.messages.create(
            from_=self.phone_number,
            body=message,
            to=to,
        )
        return twilio_message.sid
