from utils.deprecation_headers import add_deprecation_headers
from flask import Response

def test_add_deprecation_headers():
    resp = Response("test")
    add_deprecation_headers(resp, "v1")
    assert resp.headers.get("Deprecation") == "Tue, 01 Jul 2025 00:00:00 GMT"
    assert resp.headers.get("Sunset") == "Tue, 01 Jan 2026 00:00:00 GMT"

    # Test non-existent version
    resp2 = Response("test")
    add_deprecation_headers(resp2, "v999")
    assert "Deprecation" not in resp2.headers
