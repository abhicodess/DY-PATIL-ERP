import os
import re
import sys

# Regex patterns
# 1. Bare hex strings of length > 32 characters
HEX_PATTERN = re.compile(r'\b[0-9a-fA-F]{33,}\b')

# 2. Literal assignments to variables containing 'password', 'secret', or 'token'
# Matches things like: password = "my_pass", db_secret = 'xyz', auth_token = "abc"
LITERAL_ASSIGN_PATTERN = re.compile(
    r'\b(?:password|secret|token)\w*\s*=\s*([\'"])([^\'"]+)\1', 
    re.IGNORECASE
)

# 3. For .env files, checks if key has a non-placeholder value
ENV_SECRET_KEYS = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL', 'POSTGRES_PASSWORD', 'REDIS_URL']
PLACEHOLDER_SUBSTRINGS = ['change-me', 'placeholder', 'localhost', 'redis://redis', 'postgresql://postgres:postgres']

# Excluded folders to avoid false positives in dependencies/builds
EXCLUDE_DIRS = {
    '.git', '.venv', 'venv', 'node_modules', 'dist', 
    '__pycache__', '.pytest_cache', 'htmlcov', 'backups', 'uploads'
}

def audit_file(filepath):
    warnings = []
    basename = os.path.basename(filepath)
    is_env_file = filepath.endswith('.env') or (basename.startswith('.env') and basename != '.env.example')
    is_env_example = filepath.endswith('.env.example')
    
    # We don't want to raise errors on .env.example unless it contains a real value
    if is_env_example:
        return warnings

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_no, line in enumerate(f, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith('#'):
                    continue
                
                # Check for bare hex strings > 32 chars
                hex_matches = HEX_PATTERN.findall(clean_line)
                for match in hex_matches:
                    # Ignore known safe values if any, otherwise warn
                    warnings.append((line_no, f"Hardcoded hex string (>32 chars): {match[:10]}..."))
                
                if is_env_file:
                    # For .env files, warn on any key with real secrets that aren't placeholders
                    if '=' in clean_line:
                        key, value = clean_line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('\'"')
                        if value and not any(p in value.lower() for p in PLACEHOLDER_SUBSTRINGS):
                            # Special case: allow default user/db names or empty keys
                            if any(sk in key.upper() for sk in ENV_SECRET_KEYS):
                                warnings.append((line_no, f"Config secret '{key}' contains a potential live value: {value[:15]}..."))
                else:
                    # For python files, check for literal assignments
                    assign_matches = LITERAL_ASSIGN_PATTERN.findall(clean_line)
                    for quote, value in assign_matches:
                        # Ignore common placeholder names/safe dummy values
                        value_lower = value.lower()
                        if any(p in value_lower for p in PLACEHOLDER_SUBSTRINGS) or value_lower in ('', 'true', 'false', 'none'):
                            continue
                        # Warn about potential hardcoded secret
                        warnings.append((line_no, f"Literal secret assignment detected: {clean_line[:40]}..."))
                        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return warnings

def main():
    print("=== Scanning codebase for hardcoded secrets ===")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    total_warnings = 0
    scanned_files = 0
    
    for root, dirs, files in os.walk(project_root):
        # Filter out directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            # We scan all .py and .env files
            is_env = file.endswith('.env') or (file.startswith('.env') and file != '.env.example')
            if file.endswith('.py') or is_env:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, project_root)
                scanned_files += 1
                
                warnings = audit_file(filepath)
                if warnings:
                    print(f"\n[WARNING] {rel_path}:")
                    for line_no, msg in warnings:
                        print(f"  Line {line_no}: {msg}")
                    total_warnings += len(warnings)
                    
    print(f"\nScan completed. Scanned {scanned_files} files. Found {total_warnings} potential secret leakage(s).")
    
    # Return exit code based on warnings found (critical for pre-commit hooks)
    if total_warnings > 0:
        print("\n[-] FAIL: Secrets audit detected potential hardcoded secrets. Please fix before committing.")
        sys.exit(1)
    else:
        print("\n[+] SUCCESS: No hardcoded secrets detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
