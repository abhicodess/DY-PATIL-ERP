from flask import g

def get_current_tenant() -> dict:
    tenant = getattr(g, 'tenant', None)
    if tenant is None:
        # Fallback for CLI commands or scripts that initialize a mock/temp context
        # but don't run through the WSGI middleware
        raise RuntimeError(
            "No tenant in request context. "
            "TenantMiddleware may not be registered, or you are running outside a tenant-scoped request."
        )
    return tenant

def get_tenant_id() -> int:
    return get_current_tenant()['id']

def get_tenant_schema() -> str:
    return get_current_tenant()['schema_name']

def get_tenant_config(key: str, default=None) -> str:
    tenant = get_current_tenant()
    from services.tenant_service import TenantService
    return TenantService.get_config(tenant['id'], key, default)
