import pytest
from flask import g
import os
from utils.tenant_context import get_current_tenant, get_tenant_id, get_tenant_schema, get_tenant_config
from utils.tenant_storage import TenantStorage
from utils.tenant_jwt import role_required, tenant_jwt_required
import utils.tenant_jwt

def test_tenant_context_success(app):
    with app.app_context():
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        assert get_current_tenant() == g.tenant
        assert get_tenant_id() == 1
        assert get_tenant_schema() == "public"

def test_tenant_context_missing(app):
    with app.app_context():
        if hasattr(g, 'tenant'):
            delattr(g, 'tenant')
        with pytest.raises(RuntimeError):
            get_current_tenant()

def test_tenant_context_config(app, monkeypatch):
    from services.tenant_service import TenantService
    with app.app_context():
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        
        # Mock TenantService.get_config
        monkeypatch.setattr(TenantService, "get_config", lambda tenant_id, key, default=None: "custom_value" if key == "my_key" else default)
        
        assert get_tenant_config("my_key") == "custom_value"
        assert get_tenant_config("missing_key", "default_val") == "default_val"

def test_tenant_storage(app, tmp_path):
    # Set BASE_PATH to tmp_path to test physical file creation/deletion safely
    TenantStorage.BASE_PATH = str(tmp_path)
    
    with app.app_context():
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        path = TenantStorage.upload_path("test.txt")
        assert "dypatil" in path
        
        # Write dummy file
        with open(path, "w") as f:
            f.write("hello")
        assert os.path.exists(path)
        
        # Delete file
        TenantStorage.delete("test.txt")
        assert not os.path.exists(path)
        
        assert TenantStorage.download_url("test.txt") == "/uploads/dypatil/test.txt"

def test_tenant_jwt_decorator(app):
    with app.app_context():
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        
        @role_required("admin")
        def dummy_admin_route():
            return "ok"
            
        # Mock JWT claims directly in Flask globals g
        g._jwt_extended_jwt = {"role": "admin", "tenant_id": 1}
        assert dummy_admin_route() == "ok"
        
        g._jwt_extended_jwt = {"role": "student", "tenant_id": 1}
        resp = dummy_admin_route()
        assert resp[1] == 403

def test_tenant_jwt_required_decorator(app, monkeypatch):
    with app.app_context():
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        
        @tenant_jwt_required
        def dummy_jwt_route():
            return "ok"
            
        # 1. Success case
        g._jwt_extended_jwt = {"role": "admin", "tenant_id": 1}
        monkeypatch.setattr(utils.tenant_jwt, "verify_jwt_in_request", lambda: None)
        assert dummy_jwt_route() == "ok"
        
        # 2. JWT tenant mismatch
        g._jwt_extended_jwt = {"role": "admin", "tenant_id": 2}
        resp, status = dummy_jwt_route()
        assert status == 403
        
        # 3. No tenant context
        if hasattr(g, 'tenant'):
            delattr(g, 'tenant')
        resp, status = dummy_jwt_route()
        assert status == 400
        
        # 4. verify_jwt_in_request throws exception
        g.tenant = {"id": 1, "slug": "dypatil", "schema_name": "public"}
        def throw_err():
            raise Exception("token expired")
        monkeypatch.setattr(utils.tenant_jwt, "verify_jwt_in_request", throw_err)
        resp, status = dummy_jwt_route()
        assert status == 401

def test_tenant_middleware(app, monkeypatch):
    from utils.tenant_middleware import TenantMiddleware
    
    def dummy_wsgi_app(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b"ok"]
        
    middleware = TenantMiddleware(dummy_wsgi_app, flask_app=app)
    
    # 1. Admin subdomain bypass
    environ = {
        'HTTP_HOST': 'admin.dypatil.edu',
        'PATH_INFO': '/dashboard'
    }
    def start_response(status, headers):
        pass
    res = middleware(environ, start_response)
    assert environ['tenant']['slug'] == 'admin'
    assert res == [b"ok"]
    
    # 2. Health check bypass
    environ = {
        'HTTP_HOST': 'dypatil.edu',
        'PATH_INFO': '/health'
    }
    middleware(environ, start_response)
    assert environ['tenant']['slug'] == 'public'
    
    # 3. Localhost override
    environ = {
        'HTTP_HOST': 'localhost:5000',
        'HTTP_X_TENANT_SLUG': 'dypatil',
        'PATH_INFO': '/dashboard'
    }
    monkeypatch.setitem(app.config, 'TESTING', False)
    
    from services.tenant_service import TenantService
    monkeypatch.setattr(TenantService, "get_by_subdomain", lambda sub: {"id": 1, "slug": "dypatil"})
    
    middleware(environ, start_response)
    assert environ['tenant']['slug'] == 'dypatil'
    
    # 4. Unknown subdomain (404)
    environ = {
        'HTTP_HOST': 'unknown.dypatil.edu',
        'PATH_INFO': '/dashboard'
    }
    monkeypatch.setattr(TenantService, "get_by_subdomain", lambda sub: None)
    
    response_status = []
    def sr_404(status, headers):
        response_status.append(status)
    res = middleware(environ, sr_404)
    assert response_status[0] == '404 Not Found'
    
    # 5. Database exception (500)
    def db_err(sub):
        raise Exception("DB Down")
    monkeypatch.setattr(TenantService, "get_by_subdomain", db_err)
    
    response_status = []
    def sr_500(status, headers):
        response_status.append(status)
    res = middleware(environ, sr_500)
    assert response_status[0] == '500 Internal Server Error'
