# backend/core/config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "prod-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dy_patil_erp")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis for Caching / Celery
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    # Security Settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day; 50 per hour"
    RATELIMIT_STORAGE_URI = REDIS_URL
