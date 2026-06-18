import os
import re
from flask import Flask
import sys

# Add project root to path
sys.path.append('d:/DY PATIL ERP')

import core.routes_registry as routes_registry

app = Flask(__name__)

# Mocking app to get endpoints
import app as erp_app
erp_app.register_blueprints(app)

registered_endpoints = set(app.view_functions.keys())
registry_endpoints = {v['endpoint'] for v in routes_registry.ROUTES.values()}

print(f"Registered Endpoints: {len(registered_endpoints)}")
print(f"Registry Endpoints: {len(registry_endpoints)}")

TEMPLATE_DIR = 'd:/DY PATIL ERP/templates'
# Improved pattern to capture both single and double quotes
URL_FOR_PATTERN = re.compile(r"url_for\s*\(\s*['\"]([^'\"]+)['\"]")

broken_calls = []

for root, dirs, files in os.walk(TEMPLATE_DIR):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = URL_FOR_PATTERN.findall(content)
                    for endpoint in matches:
                        # Check endpoint directly or with 'static' which is default
                        if endpoint != 'static' and endpoint not in registered_endpoints:
                            # Also check if it exists via registry keys (Template might use {{ route('key') }})
                            # But here we search for url_for specifically
                            broken_calls.append({
                                "file": path.replace('\\', '/'),
                                "endpoint": endpoint
                            })
            except Exception as e:
                print(f"Error reading {path}: {e}")

import json
print(json.dumps(broken_calls, indent=2))
