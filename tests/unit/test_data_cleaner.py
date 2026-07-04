from utils.data_cleaner import clean_text, normalize_header, extract_metadata, parse_date_token, is_valid_roll

def test_clean_text():
    assert clean_text("  hello \n world  ") == "hello world"
    assert clean_text(None) == ""

def test_normalize_header():
    assert normalize_header(" Roll No. (PRN) ") == "roll_no_prn"

def test_extract_metadata():
    meta = [
        ["School of Engineering", ""],
        ["Department of Computer Engineering", ""],
        ["Academic Year 2025-26, Semester -II", ""],
        ["Program: S.Y. B.Tech Comp. Engg. (Div. A)", ""],
        ["From 19.01.2026 to 10.04.2026", ""]
    ]
    res = extract_metadata(meta)
    assert res["department"] == "CS"
    assert res["semester"] == "II"
    assert res["division"] == "A"
    assert res["date_range"]["start"] == "2026-01-19"
    assert res["date_range"]["end"] == "2026-04-10"

def test_parse_date_token():
    assert parse_date_token("19.01.2026") == "2026-01-19"
    assert parse_date_token("10/04/2026") == "2026-04-10"
    assert parse_date_token("10-04-2026") == "2026-04-10"

def test_is_valid_roll():
    assert is_valid_roll("A12") is True
    assert is_valid_roll("12") is True
    assert is_valid_roll("CS-01") is False
    assert is_valid_roll("TOTAL") is False
