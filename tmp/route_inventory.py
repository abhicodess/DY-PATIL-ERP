
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app import app
import json

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        "endpoint": rule.endpoint,
        "route": str(rule),
        "blueprint": rule.endpoint.split('.')[0] if '.' in rule.endpoint else None,
        "exists": True
    })

with open("tmp/route_inventory.json", "w", encoding="utf-8") as f:
    json.dump(routes, f, indent=4)
print("SUCCESS")
