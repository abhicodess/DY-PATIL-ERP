import celery
from flask import g

class TenantTask(celery.Task):
    _app_instance = None

    def __call__(self, *args, **kwargs):
        # Intercept tenant context ID
        tenant_id = kwargs.pop('_tenant_id', None)
        if tenant_id is None:
            raise ValueError("All Celery tasks must receive _tenant_id kwarg to ensure database isolation context.")
            
        # Cache Flask app instance on the task class to avoid expensive re-initializations
        if TenantTask._app_instance is None:
            from flask import current_app
            try:
                # Try getting the current object directly; raises RuntimeError if unbound
                app_obj = current_app._get_current_object()
                TenantTask._app_instance = app_obj
            except RuntimeError:
                import sys
                import os
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                from app import create_app
                TenantTask._app_instance = create_app()
                
            if TenantTask._app_instance is None:
                import sys
                import os
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                from app import create_app
                TenantTask._app_instance = create_app()
                
        app = TenantTask._app_instance
        with app.app_context():
            from services.tenant_service import TenantService
            tenant = TenantService.get_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found or is inactive.")
                
            g.tenant = tenant
            return self.run(*args, **kwargs)
