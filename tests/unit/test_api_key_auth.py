import pytest
import datetime
from flask import g
from utils.api_key_auth import api_key_required
import utils.api_key_auth

def test_api_key_required_decorator(app, monkeypatch):
    # Mock database qone
    monkeypatch.setattr(utils.api_key_auth, "qone", lambda q, p=None: {
        "id": 1,
        "key_hash": "dummy_hash",
        "is_active": True,
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(days=1),
        "rate_limit": 100
    })
    monkeypatch.setattr(utils.api_key_auth, "exe", lambda q, p=None: None)
    
    # Mock redis_client increment
    monkeypatch.setattr(utils.api_key_auth, "redis_client", type("MockRedis", (object,), {
        "incr": lambda self, k: 1,
        "expire": lambda self, k, t: None
    })())

    # 1. Success case with valid key
    with app.test_request_context(headers={"X-API-Key": "test-key"}):
        @api_key_required
        def dummy_route():
            return "ok"

        assert dummy_route() == "ok"
        assert g.api_key["id"] == 1

    # 2. Missing key in headers
    with app.test_request_context(headers={}):
        @api_key_required
        def dummy_route_missing():
            return "ok"
        
        response, status = dummy_route_missing()
        assert status == 401

    # 3. Invalid key in DB (key record is None)
    monkeypatch.setattr(utils.api_key_auth, "qone", lambda q, p=None: None)
    with app.test_request_context(headers={"X-API-Key": "invalid-key"}):
        @api_key_required
        def dummy_route_invalid():
            return "ok"
        
        response, status = dummy_route_invalid()
        assert status == 401

