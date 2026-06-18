import os
import secrets
from werkzeug.security import generate_password_hash

# Try importing password validator, fall back if not available yet
try:
    from utils.password_policy import validate_password
except ImportError:
    import re
    def validate_password(password):
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        return True, ""

def main():
    print("=== DY Patil ERP Secrets Rotation CLI ===")
    
    # Load existing env for defaults if it exists
    existing_env = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    existing_env[key.strip()] = val.strip()

    # Generate keys
    secret_key = secrets.token_hex(32)
    jwt_secret_key = secrets.token_hex(32)
    print(f"[+] Auto-generated new SECRET_KEY: {secret_key}")
    print(f"[+] Auto-generated new JWT_SECRET_KEY: {jwt_secret_key}")

    # Prompt for admin password
    while True:
        admin_pass = input("Enter new ADMIN password (or press Enter to keep current if available): ").strip()
        if not admin_pass and "ADMIN_PASSWORD" in existing_env:
            admin_pass = existing_env["ADMIN_PASSWORD"]
            print("[*] Keeping current admin password.")
            break
        elif not admin_pass:
            print("[-] Admin password cannot be empty. Please enter a password.")
            continue
        
        is_valid, err_msg = validate_password(admin_pass)
        if not is_valid:
            print(f"[-] Invalid password: {err_msg}")
            continue
        break

    # Hash the password with scrypt method
    hashed_pass = generate_password_hash(admin_pass, method='scrypt')
    # Escape $ for docker-compose compatibility
    escaped_hash = hashed_pass.replace('$', '$$')

    # Prompt for DATABASE_URL
    default_db = existing_env.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/erp_db")
    db_url = input(f"Enter DATABASE_URL [{default_db}]: ").strip()
    if not db_url:
        db_url = default_db

    # Prompt for REDIS_URL
    default_redis = existing_env.get("REDIS_URL", "redis://localhost:6379/0")
    redis_url = input(f"Enter REDIS_URL [{default_redis}]: ").strip()
    if not redis_url:
        redis_url = default_redis

    # Prompt for SENTRY_DSN
    default_sentry = existing_env.get("SENTRY_DSN", "")
    sentry_dsn = input(f"Enter SENTRY_DSN [{default_sentry}]: ").strip()
    if not sentry_dsn:
        sentry_dsn = default_sentry

    # Extract db password and username for POSTGRES_USER / POSTGRES_PASSWORD
    # E.g. postgresql://user:pass@host:port/db
    import urllib.parse
    postgres_user = "postgres"
    postgres_password = "password"
    postgres_db = "erp_db"
    try:
        if db_url.startswith("postgresql://"):
            parsed = urllib.parse.urlparse(db_url)
            postgres_user = parsed.username or "postgres"
            postgres_password = parsed.password or "password"
            postgres_db = parsed.path.lstrip('/') or "erp_db"
    except Exception:
        pass

    # Keep default student/faculty passwords
    default_student_pwd = existing_env.get("DEFAULT_STUDENT_PASSWORD", "D0pdb2Bg5riRvtAa")
    default_faculty_pwd = existing_env.get("DEFAULT_FACULTY_PASSWORD", "fT-_Ok4-YxUMtuKF")

    # Generate CELERY links using REDIS_URL but different database indices
    # e.g., if REDIS_URL is redis://localhost:6379/0, celery broker/backend can use index 1
    celery_broker = redis_url
    celery_backend = redis_url
    if "redis://" in redis_url:
        # change database index from /0 to /1 for Celery if it ends with /0
        if redis_url.endswith("/0"):
            celery_broker = redis_url[:-2] + "/1"
            celery_backend = redis_url[:-2] + "/1"

    # Write fresh .env
    with open(".env", "w") as f:
        f.write("# DY Patil ERP Environment Configuration (Rotated)\n\n")
        f.write("# SECURITY\n")
        f.write(f"SECRET_KEY={secret_key}\n")
        f.write(f"JWT_SECRET_KEY={jwt_secret_key}\n")
        f.write(f"DEFAULT_STUDENT_PASSWORD={default_student_pwd}\n")
        f.write(f"DEFAULT_FACULTY_PASSWORD={default_faculty_pwd}\n")
        f.write(f"ADMIN_PASSWORD={admin_pass}\n")
        f.write(f"ADMIN_PASSWORD_HASH={escaped_hash}\n\n")
        
        f.write("# DATABASE\n")
        f.write(f"DATABASE_URL={db_url}\n")
        f.write(f"DB_POOL_MAX={existing_env.get('DB_POOL_MAX', '100')}\n\n")
        
        f.write("# REDIS & CELERY\n")
        f.write(f"REDIS_URL={redis_url}\n")
        f.write(f"CELERY_BROKER_URL={celery_broker}\n")
        f.write(f"CELERY_RESULT_BACKEND={celery_backend}\n\n")
        
        f.write("# STORAGE / MONITORING\n")
        f.write(f"SENTRY_DSN={sentry_dsn}\n\n")
        
        f.write("# POSTGRES & GRAFANA\n")
        f.write(f"POSTGRES_USER={postgres_user}\n")
        f.write(f"POSTGRES_PASSWORD={postgres_password}\n")
        f.write(f"POSTGRES_DB={postgres_db}\n")
        f.write(f"GRAFANA_ADMIN_USER={existing_env.get('GRAFANA_ADMIN_USER', 'admin')}\n")
        f.write(f"GRAFANA_ADMIN_PASSWORD={existing_env.get('GRAFANA_ADMIN_PASSWORD', 'admin')}\n")

    print("[+] Fresh .env file written successfully.")

if __name__ == "__main__":
    main()
