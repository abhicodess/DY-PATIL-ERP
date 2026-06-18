import os
import logging
from datetime import datetime

# Setup logging for alerts
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

alert_logger = logging.getLogger("ShortageAlerts")
alert_logger.setLevel(logging.INFO)
handler = logging.FileHandler(os.path.join(log_dir, "shortage_alerts.log"))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
alert_logger.addHandler(handler)

def send_sms(phone, message):
    """
    Placeholder for actual SMS API Integration (e.g., Twilio, TextLocal, MSG91).
    Logs the attempt to logs/shortage_alerts.log.
    """
    if not phone or str(phone).strip() == "":
        return False, "Invalid phone number"
    
    # ACTUAL INTEGRATION POINT:
    # Example for MSG91:
    # requests.post("https://api.msg91.com/api/v5/flow/", json={"template_id": "...", "mobiles": phone, ...})
    
    alert_logger.info(f"SMS TO {phone}: {message}")
    print(f"[DEBUG] SMS TO {phone}: {message}")
    return True, "SMS Logged successfully"

def send_email(email, subject, body):
    """
    Placeholder for actual Email API Integration (e.g., SendGrid, Mailgun, SMTP).
    """
    if not email or "@" not in str(email):
        return False, "Invalid email address"
        
    alert_logger.info(f"EMAIL TO {email} (SUB: {subject}): {body}")
    print(f"[DEBUG] EMAIL TO {email}: {subject}")
    return True, "Email Logged successfully"
