import os
from .base import SMSProvider

class DummyProvider(SMSProvider):
    """Used for local development and testing without spending money."""
    def send_sms(self, recipient: str, message: str) -> dict:
        print(f"[DUMMY SMS] To: {recipient} | Msg: {message}")
        return {
            "success": True,
            "id": "DUMMY_REF_123",
            "error": None,
            "raw": {"status": "simulated"}
        }

class TwilioProvider(SMSProvider):
    def __init__(self):
        try:
            from twilio.rest import Client
            self.sid = os.environ.get("TWILIO_SID")
            self.token = os.environ.get("TWILIO_AUTH_TOKEN")
            self.from_number = os.environ.get("TWILIO_NUMBER")
            self.client = Client(self.sid, self.token)
        except ImportError:
            self.client = None
            print("Twilio library not installed. SMS will fail.")

    def send_sms(self, recipient: str, message: str) -> dict:
        if not self.client:
            return {"success": False, "error": "Twilio not configured", "raw": {}}
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient
            )
            return {
                "success": True,
                "id": msg.sid,
                "error": None,
                "raw": vars(msg)
            }
        except Exception as e:
            return {
                "success": False,
                "id": None,
                "error": str(e),
                "raw": {}
            }
