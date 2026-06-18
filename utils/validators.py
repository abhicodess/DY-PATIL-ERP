import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    # Basic 10-digit validation
    return re.match(r'^\d{10}$', str(phone)) is not None

def validate_prn(prn):
    # Example PRN validation (adjust based on actual format)
    return len(str(prn)) >= 8
