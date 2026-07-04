from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_redis import FlaskRedis
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
import os
import logging

from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
db = SQLAlchemy()
cors = CORS()
csrf = CSRFProtect()
migrate = Migrate()
# Default to memory storage to prevent crashing if Redis is down
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri=os.environ.get("REDIS_URL", "memory://")
)
redis_client = FlaskRedis()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")
from flask_smorest import Api
api = Api()

# Expose celery for task files importing from extensions
from celery_app import celery

def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    api.init_app(app)
    
    # Limiter config
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    
    # Attempt to use Redis for limiter, but fallback is already memory://
    try:
        # Check if Redis is actually up before setting it as primary storage
        import redis
        client = redis.from_url(redis_url, socket_timeout=1)
        client.ping()
        limiter.storage_uri = redis_url
        app.logger.info("Redis connected successfully for Rate Limiting.")
    except Exception:
        app.logger.warning("Redis ping failed. Rate limiting will use local memory storage.")
    
    limiter.init_app(app)
    if app.config.get("TESTING"):
        limiter.enabled = False
    redis_client.init_app(app)
    jwt.init_app(app)
    
    # Initialize SocketIO with message queue
    if app.config.get("TESTING"):
        socketio.init_app(app)
    else:
        try:
            socketio.init_app(app, message_queue=redis_url)
            app.logger.info("SocketIO initialized with Redis message queue.")
        except Exception as e:
            socketio.init_app(app)
            app.logger.warning(f"SocketIO fallback to local: {e}")

    # Token blocklist check loader
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
        jti = jwt_payload["jti"]
        try:
            token_in_redis = redis_client.get(f"jwt_blacklist:{jti}")
            return token_in_redis is not None
        except Exception as e:
            logging.error(f"Error checking token blocklist in Redis: {e}")
            return False

