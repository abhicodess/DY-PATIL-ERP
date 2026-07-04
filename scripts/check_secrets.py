import os
import sys
import zipfile
import subprocess
import re

PLACEHOLDER_SUBSTRINGS = [
    'change-me', 'placeholder', 'localhost', 'redis://redis', 
    'postgresql://postgres:postgres', 'example', 'password123', 
    'admin123', 'dummy', 'test', 'temp', 'mock', 'wrong'
]
ENV_SECRET_KEYS = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL', 'POSTGRES_PASSWORD', 'REDIS_URL']
LITERAL_ASSIGN_PATTERN = re.compile(
    r'\b(?:password|secret|token)\w*\s*=\s*([\'"])([^\'"]+)\1', 
    re.IGNORECASE
)
HEX_PATTERN = re.compile(r'\b[0-9a-fA-F]{33,}\b')

def get_tracked_files():
    try:
        output = subprocess.check_output(['git', 'ls-files'], text=True)
        return [line.strip() for line in output.split('\n') if line.strip()]
    except Exception as e:
        print(f"Error running git ls-files: {e}")
        return None

def is_ignored_by_git(filepath):
    try:
        res = subprocess.run(['git', 'check-ignore', filepath], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False

def check_file_for_secrets(filepath):
    warnings = []
    basename = os.path.basename(filepath)
    is_env_file = filepath.endswith('.env') or (basename.startswith('.env') and basename != '.env.example')
    is_env_example = filepath.endswith('.env.example')
    
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
                    warnings.append((line_no, f"Hardcoded hex string (>32 chars): {match[:10]}..."))
                
                if is_env_file:
                    if '=' in clean_line:
                        key, value = clean_line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('\'"')
                        if value and not any(p in value.lower() for p in PLACEHOLDER_SUBSTRINGS):
                            if any(sk in key.upper() for sk in ENV_SECRET_KEYS):
                                warnings.append((line_no, f"Config secret '{key}' contains a potential live value: {value[:15]}..."))
                else:
                    assign_matches = LITERAL_ASSIGN_PATTERN.findall(clean_line)
                    for quote, value in assign_matches:
                        value_lower = value.lower()
                        if any(p in value_lower for p in PLACEHOLDER_SUBSTRINGS) or value_lower in ('', 'true', 'false', 'none'):
                            continue
                        warnings.append((line_no, f"Literal secret assignment: {clean_line[:40]}..."))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return warnings

def main():
    print("=== RUNNING CI SECRETS CHECK ===")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errors_found = False
    
    # 1. Check Git tracked files
    tracked = get_tracked_files()
    if tracked:
        print(f"Checking {len(tracked)} git-tracked files...")
        for rel_path in tracked:
            basename = os.path.basename(rel_path)
            if basename.startswith('.env') and basename != '.env.example':
                print(f"[-] ERROR: Environment file '{rel_path}' is tracked by Git!")
                errors_found = True
                continue
            
            filepath = os.path.join(project_root, rel_path)
            if not os.path.exists(filepath):
                continue
                
            if rel_path.endswith('.py') or (basename.startswith('.env') and basename != '.env.example'):
                warnings = check_file_for_secrets(filepath)
                if warnings:
                    print(f"[-] ERROR: Secrets found in tracked file '{rel_path}':")
                    for line_no, msg in warnings:
                        print(f"  Line {line_no}: {msg}")
                    errors_found = True

    # 2. Check if .env is gitignored
    try:
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            if not is_ignored_by_git(env_path):
                print("[-] ERROR: '.env' exists but is NOT ignored by git!")
                errors_found = True
            else:
                print("[+] OK: '.env' is correctly gitignored.")
    except Exception as e:
        print(f"Warning: Could not check git ignore status: {e}")

    # 3. Check any .zip files in the project directory
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in {'.git', '.venv', 'venv', 'node_modules'}]
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                rel_zip = os.path.relpath(zip_path, project_root)
                
                # Skip if the ZIP itself is gitignored
                if is_ignored_by_git(zip_path):
                    print(f"[+] Skipping gitignored zip archive: '{rel_zip}'")
                    continue
                    
                print(f"Scanning zip archive '{rel_zip}' for secrets...")
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        namelist = zf.namelist()
                        for name in namelist:
                            base = os.path.basename(name)
                            if base.startswith('.env') and base != '.env.example':
                                print(f"[-] ERROR: ZIP file '{rel_zip}' contains env file '{name}'!")
                                errors_found = True
                                
                            if name.endswith('.py') or (base.startswith('.env') and base != '.env.example'):
                                try:
                                    content = zf.read(name).decode('utf-8', errors='ignore')
                                    for line_no, line in enumerate(content.split('\n'), 1):
                                        clean_line = line.strip()
                                        if not clean_line or clean_line.startswith('#'):
                                            continue
                                        hex_matches = HEX_PATTERN.findall(clean_line)
                                        if hex_matches:
                                            print(f"[-] ERROR: ZIP file '{rel_zip}' -> '{name}' contains hardcoded hex at line {line_no}")
                                            errors_found = True
                                        assign_matches = LITERAL_ASSIGN_PATTERN.findall(clean_line)
                                        for quote, val in assign_matches:
                                            val_lower = val.lower()
                                            if not any(p in val_lower for p in PLACEHOLDER_SUBSTRINGS) and val_lower not in ('', 'true', 'false', 'none'):
                                                print(f"[-] ERROR: ZIP file '{rel_zip}' -> '{name}' contains secret assignment at line {line_no}: {clean_line[:40]}...")
                                                errors_found = True
                                except Exception as e:
                                    print(f"Warning: Could not check file '{name}' in zip: {e}")
                except Exception as e:
                    print(f"Warning: Could not open ZIP file '{rel_zip}': {e}")

    if errors_found:
        print("\n[-] FAIL: Secrets hygiene check failed. Please resolve the errors above.")
        sys.exit(1)
    else:
        print("\n[+] SUCCESS: Secrets hygiene check passed.")
        sys.exit(0)

if __name__ == '__main__':
    main()
