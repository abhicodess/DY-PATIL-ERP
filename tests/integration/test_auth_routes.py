import pytest
from flask import session as flask_session

def test_login_page_loads(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data

def test_login_invalid_credentials(client):
    response = client.post("/auth/login", data={
        "role": "faculty",
        "username": "wrong",
        "password": "wrong"
    }, follow_redirects=True)
    assert b"Invalid faculty credentials." in response.data

def test_logout(client):
    # Mocking a session for logout
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
    
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_brute_force_lockout_mechanism(client, monkeypatch):
    import extensions
    
    class MockRedis:
        def __init__(self):
            self.lockout = None
            self.attempts = 0
            self.incr_called_with = None
            
        def get(self, key):
            if "lockout" in key:
                return self.lockout
            return None
            
        def incr(self, key):
            self.incr_called_with = key
            self.attempts += 1
            return self.attempts
            
        def expire(self, key, time):
            pass
            
        def delete(self, key):
            pass
            
        def set(self, key, val, ex=None):
            pass
            
    mock_redis = MockRedis()
    monkeypatch.setattr(extensions, "redis_client", mock_redis)
    
    # 1. When not locked out
    mock_redis.lockout = None
    response = client.post("/api/v1/auth/login", json={
        "username": "wrong",
        "password": "wrong",
        "role": "faculty"
    })
    assert response.status_code in (401, 422)
    assert mock_redis.incr_called_with == "attempts:wrong"

    # 2. When locked out
    mock_redis.lockout = 1
    response = client.post("/api/v1/auth/login", json={
        "username": "locked_user",
        "password": "password",
        "role": "faculty"
    })
    assert response.status_code == 423
    assert b"Account locked. Try again in 10 minutes." in response.data
