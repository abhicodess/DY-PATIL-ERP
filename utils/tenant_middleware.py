import json
import logging
from services.tenant_service import TenantService

logger = logging.getLogger("tenant_middleware")

class TenantMiddleware:
    def __init__(self, app, flask_app=None):
        self.app = app
        self.flask_app = flask_app

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', '')
        host_name = host.split(':')[0]
        subdomain = host_name.split('.')[0]
        
        # Localhost development override via custom header
        if 'localhost' in host_name or '127.0.0.1' in host_name:
            # Check for standard HTTP headers (WSGI prefixes custom headers with HTTP_)
            subdomain = environ.get('HTTP_X_TENANT_SLUG') or environ.get('HTTP_X_TENANT_SUBDOMAIN') or 'default'
            
        # Bypass or permit superadmin requests
        if subdomain == 'admin':
            environ['tenant'] = {
                "id": 0,
                "slug": "admin",
                "subdomain": "admin",
                "schema_name": "public",
                "is_active": True
            }
            return self.app(environ, start_response)
            
        # Global health check and metrics endpoint bypass
        path = environ.get('PATH_INFO', '')
        if path in ('/health', '/health/', '/metrics', '/metrics/'):
            environ['tenant'] = {
                "id": 1,
                "slug": "public",
                "subdomain": "public",
                "schema_name": "public",
                "is_active": True
            }
            return self.app(environ, start_response)

        # Check if testing
        is_testing = self.flask_app and self.flask_app.config.get('TESTING')

        if is_testing or subdomain == 'default':
            environ['tenant'] = {
                "id": 1,
                "slug": "dypatil",
                "name": "DY Patil University",
                "subdomain": "dypatil",
                "schema_name": "public",
                "is_active": True
            }
            return self.app(environ, start_response)

        # Wrap in Flask application context for safe DB querying
        try:
            if self.flask_app:
                with self.flask_app.app_context():
                    tenant = TenantService.get_by_subdomain(subdomain)
            else:
                tenant = TenantService.get_by_subdomain(subdomain)
        except Exception as e:
            logger.error(f"Database error in TenantMiddleware: {e}", exc_info=True)
            start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
            return [json.dumps({
                "error": "Internal Database Error. Please try again later.",
                "code": "DATABASE_ERROR"
            }).encode('utf-8')]
 
        if not tenant:
            start_response('404 Not Found', [('Content-Type', 'application/json')])
            return [json.dumps({
                "error": f"Institution portal for subdomain '{subdomain}' is not registered or is inactive."
            }).encode('utf-8')]
                
        environ['tenant'] = tenant

        return self.app(environ, start_response)
