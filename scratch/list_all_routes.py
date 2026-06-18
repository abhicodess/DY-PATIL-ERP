import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_secret_key_placeholder_for_script_32_chars"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_placeholder_for_script_32_chars"
os.environ["DATABASE_URL"] = "postgresql://postgres:2233@localhost:5432/erp_db"
os.environ["POSTGRES_PASSWORD"] = "2233"

from app import create_app

app = create_app()

print(f"{'Endpoint':<45} | {'Methods':<15} | {'Path'}")
print("-" * 120)
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    methods = sorted(list(rule.methods - {'OPTIONS', 'HEAD'}))
    if not methods:
        continue
    print(f"{rule.endpoint:<45} | {str(methods):<15} | {rule}")
