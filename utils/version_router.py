import importlib
import re
from flask import jsonify, request

VERSION_CONFIGS = {
  "v1": {
    "prefix":       "/api/v1",
    "status":       "stable",       # stable | deprecated | sunset
    "released":     "2024-01-15",
    "deprecated":   None,           # date deprecation was announced
    "sunset":       None,           # date v1 will stop working
    "blueprints":   "blueprints.v1"
  },
  "v2": {
    "prefix":       "/api/v2",
    "status":       "stable",
    "released":     None,           # not yet released
    "deprecated":   None,
    "sunset":       None,
    "blueprints":   "blueprints.v2"
  }
}

def get_next_version(version: str) -> str:
    if version == "v1":
        return "v2"
    return "v3"

def extract_version_from_path(path: str) -> str:
    m = re.match(r'^/api/(v[0-9]+)', path)
    return m.group(1) if m else None

def sunset_handler(version: str):
    config = VERSION_CONFIGS.get(version)
    if not config or config['status'] != 'sunset':
        return None
    return jsonify({
        "error": f"API version {version} has been sunsetted as of {config['sunset']}.",
        "code": "VERSION_SUNSETTED",
        "migrate_to": f"/api/{get_next_version(version)}/",
        "migration_guide": f"https://yourerp.com/docs/migration/{version}-to-{get_next_version(version)}",
        "sunset_date": config['sunset']
    }), 410

def register_versioned_blueprints(app, api):
    for version, config in VERSION_CONFIGS.items():
        if config['status'] == 'sunset':
            continue
        try:
            module = importlib.import_module(config['blueprints'])
            for bp in module.BLUEPRINTS:
                api.register_blueprint(bp)
        except (ImportError, AttributeError) as e:
            # If v2 is not yet initialized or doesn't have BLUEPRINTS list, skip gracefully
            if version == "v1":
                raise e
