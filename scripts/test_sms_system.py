import os
# Ensure we use the Dummy provider for testing
os.environ["SMS_PROVIDER"] = "dummy"

from services.sms_service import SMSService

def test_sms_system():
    print("Testing SMS System...")
    recipient = "+919876543210"
    template = "welcome_msg"
    context = {"name": "Senior Architect"}
    
    print(f"Sending '{template}' to {recipient}...")
    result = SMSService.send_immediate(recipient, template, context)
    
    if result['success']:
        print(f" [✓] Success! Log ID: {result['log_id']}")
        print(f" [✓] Message: {result['raw']}")
    else:
        print(f" [✗] Failed: {result['error']}")

if __name__ == "__main__":
    test_sms_system()
