import importlib
import pytest
import os

# Mock dotenv.load_dotenv to do nothing during config reload/tests
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: None

import config as config_module

def test_jwt_secret_key_required(monkeypatch):
    """App must refuse to start if JWT_SECRET_KEY is unset."""
    monkeypatch.delenv('JWT_SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError, match='JWT_SECRET_KEY'):
        importlib.reload(config_module)

def test_jwt_secret_key_too_short(monkeypatch):
    """App must refuse to start if JWT_SECRET_KEY is under 32 chars."""
    monkeypatch.setenv('JWT_SECRET_KEY', 'tooshort')
    with pytest.raises(RuntimeError, match='too short'):
        importlib.reload(config_module)

def test_secret_key_required(monkeypatch):
    """App must refuse to start if SECRET_KEY is unset."""
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        importlib.reload(config_module)
