from abc import ABC, abstractmethod

class SMSProvider(ABC):
    """
    Standard interface for all SMS providers.
    Every new provider (Twilio, MSG91, AWS) must implement this.
    """
    
    @abstractmethod
    def send_sms(self, recipient: str, message: str) -> dict:
        """
        Sends an SMS and returns a unified response format.
        Response Format:
        {
            "success": bool,
            "id": str (Provider Reference ID),
            "error": str (if success is False),
            "raw": dict (Original response from provider)
        }
        """
        pass
