import json
import logging
from extensions import redis_client
from utils.pg_wrapper import qone, exe, qry

logger = logging.getLogger("tenant_service")

class TenantService:
    @staticmethod
    def get_by_subdomain(subdomain: str) -> dict | None:
        cache_key = f"tenant:sub:{subdomain}"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis get failed in get_by_subdomain: {e}")
            
        # Select from public schema
        tenant = qone("SELECT * FROM public.tenants WHERE subdomain = %s AND is_active = true", (subdomain,))
        if not tenant:
            return None
            
        tenant_dict = dict(tenant)
        # Convert datetime objects to string/ISO format for JSON serialization
        if tenant_dict.get('created_at'):
            tenant_dict['created_at'] = tenant_dict['created_at'].isoformat()
        if tenant_dict.get('expires_at'):
            tenant_dict['expires_at'] = tenant_dict['expires_at'].isoformat()
            
        try:
            redis_client.setex(cache_key, 300, json.dumps(tenant_dict))
        except Exception as e:
            logger.error(f"Redis set failed in get_by_subdomain: {e}")
            
        return tenant_dict

    @staticmethod  
    def get_by_id(tenant_id: int) -> dict | None:
        cache_key = f"tenant:id:{tenant_id}"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis get failed in get_by_id: {e}")
            
        tenant = qone("SELECT * FROM public.tenants WHERE id = %s AND is_active = true", (tenant_id,))
        if not tenant:
            return None
            
        tenant_dict = dict(tenant)
        if tenant_dict.get('created_at'):
            tenant_dict['created_at'] = tenant_dict['created_at'].isoformat()
        if tenant_dict.get('expires_at'):
            tenant_dict['expires_at'] = tenant_dict['expires_at'].isoformat()
            
        try:
            redis_client.setex(cache_key, 300, json.dumps(tenant_dict))
        except Exception as e:
            logger.error(f"Redis set failed in get_by_id: {e}")
            
        return tenant_dict

    @staticmethod
    def get_config(tenant_id: int, key: str, default=None) -> str:
        cache_key = f"tenant:cfg:{tenant_id}:{key}"
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis get failed in get_config: {e}")
            
        config = qone("SELECT value FROM public.tenant_configs WHERE tenant_id = %s AND key = %s", (tenant_id, key))
        value = config['value'] if config else default
        
        try:
            redis_client.setex(cache_key, 300, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set failed in get_config: {e}")
            
        return value

    @staticmethod
    def bust_cache(tenant_id: int, subdomain: str):
        try:
            redis_client.delete(f"tenant:sub:{subdomain}")
            redis_client.delete(f"tenant:id:{tenant_id}")
            # Locate all config keys for this tenant and invalidate them
            config_pattern = f"tenant:cfg:{tenant_id}:*"
            keys = redis_client.keys(config_pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache bust failed for tenant {tenant_id}: {e}")

    @staticmethod
    def provision_tenant(slug, name, subdomain, plan, max_students=5000, max_faculty=500) -> dict:
        schema_name = f"tenant_{slug}"
        
        # Check if already exists in public.tenants
        existing = qone("SELECT id FROM public.tenants WHERE slug = %s", (slug,))
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists.")
            
        exe(
            """
            INSERT INTO public.tenants (slug, name, subdomain, schema_name, plan, max_students, max_faculty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (slug, name, subdomain, schema_name, plan, max_students, max_faculty)
        )
        
        tenant = qone("SELECT * FROM public.tenants WHERE slug = %s", (slug,))
        
        # Execute DDL to spin up isolated schema & apply database tables
        TenantService._create_tenant_schema(schema_name)
        TenantService._run_tenant_migrations(schema_name, slug)
        
        # Log event to audit logs
        exe(
            """
            INSERT INTO public.audit_log (action, tenant_slug, performed_by, payload)
            VALUES ('provision_tenant', %s, 'system', %s)
            """,
            (slug, f"Provisioned tenant '{name}' with schema '{schema_name}'")
        )
        
        tenant_dict = dict(tenant)
        if tenant_dict.get('created_at'):
            tenant_dict['created_at'] = tenant_dict['created_at'].isoformat()
        if tenant_dict.get('expires_at'):
            tenant_dict['expires_at'] = tenant_dict['expires_at'].isoformat()
            
        return tenant_dict

    @staticmethod
    def _create_tenant_schema(schema_name: str):
        # Enforce alphanumeric + underscore identifiers to prevent SQL injection in DDL
        safe_schema = "".join([c for c in schema_name if c.isalnum() or c == '_'])
        if safe_schema != schema_name:
            raise ValueError(f"Invalid characters in schema name '{schema_name}'")
        exe(f"CREATE SCHEMA IF NOT EXISTS {safe_schema}")

    @staticmethod
    def _run_tenant_migrations(schema_name: str, slug: str):
        import os
        from flask_migrate import upgrade as flask_migrate_upgrade
        
        # Inject context variables for migrations/env.py
        os.environ["TENANT_SCHEMA"] = schema_name
        os.environ["TENANT_SLUG"] = slug
        
        try:
            flask_migrate_upgrade()
        finally:
            os.environ.pop("TENANT_SCHEMA", None)
            os.environ.pop("TENANT_SLUG", None)
