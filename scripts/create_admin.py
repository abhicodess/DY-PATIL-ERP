import os
import sys
from werkzeug.security import generate_password_hash

def main():
    print("=== College ERP Admin Creation Helper ===")
    
    # Retrieve credentials from environment
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("Error: ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set.", file=sys.stderr)
        print("Usage on Render Shell:", file=sys.stderr)
        print("  export ADMIN_EMAIL=admin@dypatil.edu", file=sys.stderr)
        print("  export ADMIN_PASSWORD=your_secure_password", file=sys.stderr)
        print("  python scripts/create_admin.py", file=sys.stderr)
        sys.exit(1)
        
    if len(admin_password) < 8:
        print("Error: ADMIN_PASSWORD must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)
        
    # Generate the password hash using scrypt (matching blueprints/auth/routes.py)
    pwd_hash = generate_password_hash(admin_password, method='scrypt')
    
    print("\n[SUCCESS] Admin configuration generated successfully!")
    print(f"Admin Email: {admin_email}")
    print(f"Admin Username: admin (Username for login is 'admin')")
    print(f"Generated Hash: {pwd_hash}\n")
    
    # Render env vars require escaping '$' as '$$' if using docker-compose, but not in Render UI env settings.
    # We will output both styles.
    print("--- Render Environment Settings ---")
    print("Add these environment variables to your Render Environment Group:")
    print(f"ADMIN_PASSWORD: {admin_password}")
    print(f"ADMIN_PASSWORD_HASH: {pwd_hash}")
    print("-----------------------------------\n")

    # Update or create local .env if it exists
    env_path = ".env"
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
                
        new_lines = []
        has_pass = False
        has_hash = False
        
        # We need to escape '$' as '$$' in the .env file for docker-compose parsing
        escaped_hash = pwd_hash.replace('$', '$$')
        
        for line in lines:
            if line.strip().startswith("ADMIN_PASSWORD="):
                new_lines.append(f"ADMIN_PASSWORD={admin_password}\n")
                has_pass = True
            elif line.strip().startswith("ADMIN_PASSWORD_HASH="):
                new_lines.append(f"ADMIN_PASSWORD_HASH={escaped_hash}\n")
                has_hash = True
            else:
                new_lines.append(line)
                
        if not has_pass:
            new_lines.append(f"ADMIN_PASSWORD={admin_password}\n")
        if not has_hash:
            new_lines.append(f"ADMIN_PASSWORD_HASH={escaped_hash}\n")
            
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        print(f"Updated {env_path} file with new admin credentials.")
        
    except Exception as e:
        print(f"Note: Could not update local .env file ({e}). Outputting values instead.")

if __name__ == "__main__":
    main()
