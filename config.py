import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Blocker 1: secrets check configuration
REQUIRED_SECRETS = [
    'SECRET_KEY', 'JWT_SECRET_KEY', 
    'DATABASE_URL', 'POSTGRES_PASSWORD'
]
WEAK_VALUES = [
    'dev', 'secret', 'admin', 'password', 
    'changeme', 'your-secret-key', '2233',
    'admin123', 'test'
]

def secrets_check():
    for key in REQUIRED_SECRETS:
        val = os.environ.get(key, '')
        if not val:
            raise RuntimeError(f"{key} is not set")
        if val in WEAK_VALUES:
            raise RuntimeError(f"{key} is too weak")
        if 'KEY' in key and len(val) < 32:
            raise RuntimeError(f"{key} is too short (must be 32+ chars)")

class Config:
    # Security - SECRET_KEY check
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; "
            "print(secrets.token_hex(32))\""
        )
    if len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY is too short (must be 32+ chars)")
    
    # Security - JWT_SECRET_KEY check
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; "
            "print(secrets.token_hex(32))\""
        )
    if len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY is too short (must be 32+ chars)")

    # Database
    PG_URL = os.environ.get("PG_URL") or os.environ.get("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = PG_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 1800
    
    # CSRF Protection
    # Flask-WTF global CSRFProtect is DISABLED because the app uses its own
    # custom _csrf_init_and_validate before_request hook for CSRF validation.
    # Having both active causes 400 errors on login (Flask-WTF's session token
    # was never seeded, so it rejects all POSTs before our middleware runs).
    WTF_CSRF_ENABLED = False
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_FIELD_NAME = '_csrf'
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
    
    # Redis & Limiter
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT Configurations
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'
    
    # Session Security
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # File Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_PATH", "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 # 10MB
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.pdf', '.csv', '.jpg', '.png', '.jpeg'}
    
    # ERP Constants
    DEPARTMENTS  = ["AIML", "AIDS", "CS", "IT"]
    DIVISIONS    = ["A", "B", "C", "D"]
    SEMESTERS    = ["I","II","III","IV","V","VI","VII","VIII"]
    DESIGNATIONS = ["Professor","Associate Professor","Assistant Professor","Lecturer","HOD"]
    YEARS        = ["I","II","III","IV"]
    DAYS         = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    DAY_ORD      = ("CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 "
                    "WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 "
                     "WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END")
    
    # Auth Defaults
    DEFAULT_STUDENT_PASSWORD = os.environ.get("DEFAULT_STUDENT_PASSWORD")
    DEFAULT_FACULTY_PASSWORD = os.environ.get("DEFAULT_FACULTY_PASSWORD")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
    if ADMIN_PASSWORD_HASH:
        ADMIN_PASSWORD_HASH = ADMIN_PASSWORD_HASH.replace("$$", "$")
    
    # UI Mode: Serve React SPA UI instead of legacy Jinja templates
    SERVE_REACT_SPA = os.environ.get("SERVE_REACT_SPA", "False").lower() == "true"
    
    @staticmethod
    def init_app(app):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 28800

    @classmethod
    def validate(cls):
        # Enforce SECRET_KEY check
        SECRET_KEY = os.environ.get('SECRET_KEY')
        if not SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable is not set. "
                "Generate one with: python -c \"import secrets; "
                "print(secrets.token_hex(32))\""
            )

        # Enforce JWT_SECRET_KEY check
        JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
        if not JWT_SECRET_KEY:
            raise RuntimeError(
                "JWT_SECRET_KEY environment variable is not set. "
                "Generate one with: python -c \"import secrets; "
                "print(secrets.token_hex(32))\""
            )

        # Enforce DATABASE_URL check
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Please provide a valid database connection string."
            )

        # Enforce POSTGRES_PASSWORD check
        POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
        if not POSTGRES_PASSWORD:
            raise RuntimeError(
                "POSTGRES_PASSWORD environment variable is not set. "
                "Please provide a strong password for PostgreSQL."
            )

# Module-level aliases for backwards compatibility and easy importing
DEPARTMENTS = Config.DEPARTMENTS
DIVISIONS = Config.DIVISIONS
SEMESTERS = Config.SEMESTERS
DESIGNATIONS = Config.DESIGNATIONS
YEARS = Config.YEARS
DAYS = Config.DAYS
DAY_ORD = Config.DAY_ORD
