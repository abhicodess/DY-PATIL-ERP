
import os
import re

endpoints = set()
with open("tmp/route_inventory.json", "r", encoding="utf-8") as f:
    import json
    routes = json.load(f)
    for r in routes:
        endpoints.add(r['endpoint'])

re_url_for = re.compile(r"url_for\(['\"]([^'\"]+)['\"]")

broken = []

for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith((".py", ".html")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = re_url_for.findall(content)
                    for m in matches:
                        if m not in endpoints:
                            # Try to find if it's dynamic or has args
                            broken.append({"file": path, "endpoint": m})
            except:
                pass

with open("tmp/broken_routes.json", "w", encoding="utf-8") as f:
    json.dump(broken, f, indent=4)

print(f"Audit complete. Found {len(broken)} potentially broken routes.")
