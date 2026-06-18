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
