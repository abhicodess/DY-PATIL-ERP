import os
import re
import sys

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import app

def scan_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "url": str(rule)
        })
    return routes

if __name__ == "__main__":
    import json
    print(json.dumps(scan_routes(), indent=2))
