from utils.password_policy import validate_password

def test_validate_password():
    # Valid password
    is_valid, msg = validate_password("ValidPass123!")
    assert is_valid is True
    assert msg == ""

    # Too short
    is_valid, msg = validate_password("Short1!")
    assert is_valid is False
    assert "at least 12 characters" in msg

    # No uppercase
    is_valid, msg = validate_password("validpass123!")
    assert is_valid is False
    assert "one uppercase letter" in msg

    # No digit
    is_valid, msg = validate_password("ValidPass!!!!")
    assert is_valid is False
    assert "one digit" in msg

    # No special character
    is_valid, msg = validate_password("ValidPassword123")
    assert is_valid is False
    assert "one special character" in msg
