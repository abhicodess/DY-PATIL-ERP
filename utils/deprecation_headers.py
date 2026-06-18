DEPRECATION_CONFIG = {
  "v1": {
    "Deprecation":  "Tue, 01 Jul 2025 00:00:00 GMT",
    "Sunset":       "Tue, 01 Jan 2026 00:00:00 GMT",
    "Link":         '<https://yourerp.com/api/docs/migration-v1-v2>; rel="deprecation"',
    "Warning":      '299 - "API version v1 is deprecated. Migrate to v2 by 2026-01-01."'
  }
}

def add_deprecation_headers(response, version: str):
    config = DEPRECATION_CONFIG.get(version)
    if not config:
        return response
    for header, value in config.items():
        response.headers[header] = value
    return response
