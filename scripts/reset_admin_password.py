import os
import sys
from werkzeug.security import generate_password_hash

# Ensure we can import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.password_policy import validate_password

def main():
    print("=== Admin Password Reset Tool ===")
    
    if not os.path.exists(".env"):
        print("[-] Error: .env file does not exist. Run rotate_secrets.py first.")
        sys.exit(1)
        
    while True:
        password = input("Enter new ADMIN password: ").strip()
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            print(f"[-] Invalid password: {error_msg}")
            continue
        break
        
    # Hash password using scrypt
    hashed = generate_password_hash(password, method='scrypt')
    escaped_hash = hashed.replace('$', '$$')
    
    # Read existing .env lines
    lines = []
    with open(".env", "r") as f:
        lines = f.readlines()
        
    updated_password = False
    updated_hash = False
    
    new_lines = []
    for line in lines:
        if line.strip().startswith("ADMIN_PASSWORD="):
            new_lines.append(f"ADMIN_PASSWORD={password}\n")
            updated_password = True
        elif line.strip().startswith("ADMIN_PASSWORD_HASH="):
            new_lines.append(f"ADMIN_PASSWORD_HASH={escaped_hash}\n")
            updated_hash = True
        else:
            new_lines.append(line)
            
    # If the variables were not present, append them
    if not updated_password:
        new_lines.append(f"ADMIN_PASSWORD={password}\n")
    if not updated_hash:
        new_lines.append(f"ADMIN_PASSWORD_HASH={escaped_hash}\n")
        
    with open(".env", "w") as f:
        f.writelines(new_lines)
        
    print("[+] Successfully reset admin password and updated .env file.")

if __name__ == "__main__":
    main()
