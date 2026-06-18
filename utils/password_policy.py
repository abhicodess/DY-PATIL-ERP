import re

def validate_password(password):
    """
    Validates a password against the strength policy:
    - Minimum 12 characters
    - At least 1 uppercase letter
    - At least 1 digit
    - At least 1 special character
    
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""
