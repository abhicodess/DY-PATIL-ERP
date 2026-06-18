# backend/core/app_factory.py
from flask import Flask
from backend.core.extensions import db, ma, redis_client, limiter, cors
from backend.core.middleware.logging_middleware import log_request_info, log_response_info

def create_app(config_object="backend.core.config.Config"):
    """
    Enterprise App Factory.
    Initializes all extensions and registers modular blueprints.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)

    # 1. Initialize Extensions
    db.init_app(app)
    ma.init_app(app)
    redis_client.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, supports_credentials=True)

    # 2. Register Global Middleware
    @app.before_request
    def before():
        log_request_info()

    @app.after_request
    def after(response):
        return log_response_info(response)

    # 3. Register API Blueprints (v1)
    from backend.core.api.v1.auth.routes import auth_api
    from backend.core.api.v1.attendance.routes import attendance_api
    
    app.register_blueprint(auth_api, url_prefix='/api/v1/auth')
    app.register_blueprint(attendance_api, url_prefix='/api/v1/attendance')

    # 4. Global Error Handlers (Enterprise Standard)
    @app.errorhandler(404)
    def not_found(e):
        return {"message": "Resource not found", "error": str(e)}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"message": "Internal server error", "error": "An unexpected error occurred"}, 500

    return app
