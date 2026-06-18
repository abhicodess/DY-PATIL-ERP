from flask import request

def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        # Do NOT set these on static file responses
        if request.path.startswith('/static'):
            return response
            
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
