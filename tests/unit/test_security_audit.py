import os
from utils.security_audit import check_sql_injection

def test_check_sql_injection(tmp_path):
    # Create a temp python file containing both insecure and secure SQL calls
    test_file = tmp_path / "dummy_db_code.py"
    test_file.write_text("""
def bad_func(table_name, user_id):
    # Insecure f-string query
    qry(f"SELECT * FROM {table_name}")
    # Insecure % formatting
    exe("SELECT * FROM students WHERE id = %s" % user_id)
    # Insecure .format()
    qone("SELECT * FROM faculty WHERE name = '{}'".format(table_name))
    # Insecure concatenation
    exe("SELECT * FROM config WHERE key = " + table_name)

def good_func(user_id):
    # Secure parameterized query
    qry("SELECT * FROM students WHERE id = :id", {"id": user_id})
    # Non-SQL f-string
    print(f"Log user ID: {user_id}")
""")
    
    issues = check_sql_injection(str(test_file))
    # We expect 4 SQL injection issues to be caught
    assert len(issues) == 4
    messages = [msg for line, msg in issues]
    assert any("f-string SQL" in msg for msg in messages)
    assert any("% formatting SQL" in msg for msg in messages)
    assert any(".format() SQL" in msg for msg in messages)
    assert any("String concatenation SQL" in msg for msg in messages)

def test_check_sql_injection_invalid_file(tmp_path):
    from utils.security_audit import check_sql_injection
    # Create empty file
    test_file = tmp_path / "empty.py"
    test_file.touch()
    issues = check_sql_injection(str(test_file))
    assert issues == []

def test_audit_project(tmp_path, capsys):
    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    test_file = test_dir / "insecure.py"
    test_file.write_text("exe('SELECT * FROM students WHERE id = ' + user_id)")
    
    from utils.security_audit import audit_project
    audit_project(str(test_dir))
    
    captured = capsys.readouterr()
    assert "Potential SQL Injection" in captured.out
    assert "Total potential issues found: 1" in captured.out

