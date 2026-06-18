import ast
import os

def check_sql_injection(file_path):
    """
    Scans a Python file for potential SQL injection patterns.
    Looks for string formatting (f-strings, .format, %) inside DB execute/qry calls.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except Exception as e:
            print(f"Skipping {file_path}: {e}")
            return []

    issues = []
    
    db_methods = {'execute', 'qry', 'qone', 'exe', 'safe_fetch_all', 'safe_fetch_scalar'}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a call to a DB method
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            
            if func_name in db_methods:
                if not node.args:
                    continue
                
                sql_arg = node.args[0]
                
                # Pattern 1: f-strings
                if isinstance(sql_arg, ast.JoinedStr):
                    issues.append((node.lineno, f"f-string SQL detected in {func_name}"))
                
                # Pattern 2: % formatting or .format()
                elif isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, ast.Mod):
                    issues.append((node.lineno, f"% formatting SQL detected in {func_name}"))
                
                elif isinstance(sql_arg, ast.Call) and isinstance(sql_arg.func, ast.Attribute) and sql_arg.func.attr == 'format':
                    issues.append((node.lineno, f".format() SQL detected in {func_name}"))
                
                # Pattern 3: String concatenation
                elif isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, ast.Add):
                    issues.append((node.lineno, f"String concatenation SQL detected in {func_name}"))

    return issues

def audit_project(directory):
    total_issues = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "security_audit.py":
                path = os.path.join(root, file)
                file_issues = check_sql_injection(path)
                if file_issues:
                    print(f"\nPotential SQL Injection in {path}:")
                    for line, msg in file_issues:
                        print(f"  Line {line}: {msg}")
                    total_issues += len(file_issues)
    
    print(f"\nAudit complete. Total potential issues found: {total_issues}")

if __name__ == "__main__":
    audit_project(".")
