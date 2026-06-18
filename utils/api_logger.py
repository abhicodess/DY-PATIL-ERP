import time
import uuid
from flask import request, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from utils.pg_wrapper import exe

def init_api_logger(app):
    """Register before and after request handlers for API logging."""
    
    @app.before_request
    def before_api_request():
        # Only log /api/* routes
        if not request.path.startswith('/api/'):
            return
            
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())

    @app.after_request
    def after_api_request(response):
        # Only log /api/* routes
        if not request.path.startswith('/api/'):
            return response

        # Add Request ID and API Version header
        req_id = getattr(g, 'request_id', str(uuid.uuid4()))
        response.headers['X-Request-ID'] = req_id
        response.headers['X-API-Version'] = '1.0'

        # Calculate duration
        start_time = getattr(g, 'start_time', None)
        duration_ms = 0
        if start_time:
            duration_ms = int((time.time() - start_time) * 1000)

        # Get user identity from JWT safely
        user_id = None
        try:
            # check if JWT request verification was successful or exists in headers
            if 'Authorization' in request.headers:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
                if identity:
                    # Identity is typically user_id or username
                    # For token endpoint we store user_id or email
                    user_id = int(identity) if str(identity).isdigit() else None
        except Exception:
            pass

        # Parse request metadata
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        # Split in case of comma separated proxies
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

        user_agent = request.headers.get('User-Agent', '')[:255]
        method = request.method
        path = request.path[:255]
        status_code = response.status_code

        # Write to api_request_logs table
        try:
            exe(
                """
                INSERT INTO api_request_logs (
                    method, path, status_code, response_time_ms, user_id, ip_address, user_agent, request_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (method, path, status_code, duration_ms, user_id, ip_address, user_agent, req_id)
            )
        except Exception as e:
            app.logger.error(f"Failed to log API request: {e}")

        return response
