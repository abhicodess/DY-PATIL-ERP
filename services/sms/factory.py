import os
from .twilio_gw import TwilioProvider, DummyProvider

class SMSFactory:
    """
    Selects the active SMS provider based on environment variables.
    Defaults to DummyProvider for safety.
    """
    @staticmethod
    def get_provider():
        p_type = os.environ.get("SMS_PROVIDER", "dummy").lower()
        
        if p_type == "twilio":
            return TwilioProvider()
        # You can add more providers here (Fast2SMS, AWS, etc.)
        
        return DummyProvider()
