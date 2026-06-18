import os
import sys
from collections import defaultdict

# Put project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment to bypass production guards if needed
os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_secret_key_placeholder_for_script"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_placeholder_for_script"
os.environ["DATABASE_URL"] = "postgresql://postgres:2233@localhost:5432/erp_db"
os.environ["POSTGRES_PASSWORD"] = "2233"

from app import create_app

app = create_app()

print("Auditing routes...")
rules_by_path = defaultdict(list)

for rule in app.url_map.iter_rules():
    # Group by path rule
    path = str(rule)
    methods = sorted(list(rule.methods - {'OPTIONS', 'HEAD'}))
    if not methods:
        continue
    rules_by_path[path].append({
        'endpoint': rule.endpoint,
        'methods': methods
    })

duplicates = {}
for path, rules in rules_by_path.items():
    if len(rules) > 1:
        # Check if there are actual method overlaps or duplicate path definitions
        duplicates[path] = rules

print("\n--- DUPLICATE PATHS DETECTED ---")
for path, rules in sorted(duplicates.items()):
    print(f"\nPath: {path}")
    for r in rules:
        print(f"  Endpoint: {r['endpoint']} | Methods: {r['methods']}")
