import os
from flask import request, jsonify
from blueprints.superadmin import superadmin_bp
from services.tenant_service import TenantService
from utils.pg_wrapper import qry, qone, exe, get_public_db
from utils.cache import tenant_redis
from flask_jwt_extended import create_access_token
from datetime import timedelta, datetime

def _require_superadmin_auth():
    api_key = request.headers.get("X-Superadmin-Key")
    expected_key = os.environ.get("SUPERADMIN_API_KEY", "super-secret-admin-key-change-me")
    if not api_key or api_key != expected_key:
        return False
    return True

@superadmin_bp.before_request
def before_request():
    if not _require_superadmin_auth():
        return jsonify({"error": "Unauthorized superadmin access."}), 401

@superadmin_bp.route("/tenants", methods=["GET"])
def list_tenants():
    tenants = qry("SELECT * FROM public.tenants ORDER BY id")
    res = []
    for t in tenants:
        student_count = 0
        try:
            with get_public_db() as cur:
                cur.execute(f"SET search_path TO {t['schema_name']}, public")
                cur.execute("SELECT COUNT(*) as count FROM students WHERE is_active = true")
                row = cur.fetchone()
                student_count = row['count'] if row else 0
        except Exception:
            student_count = 0
            
        res.append({
            "slug": t["slug"],
            "name": t["name"],
            "subdomain": t["subdomain"],
            "plan": t["plan"],
            "student_count": student_count,
            "is_active": t["is_active"],
            "expires_at": t["expires_at"].isoformat() if t["expires_at"] else None
        })
    return jsonify(status="success", data=res)

@superadmin_bp.route("/tenants", methods=["POST"])
def provision_tenant():
    data = request.get_json() or {}
    slug = data.get("slug")
    name = data.get("name")
    subdomain = data.get("subdomain")
    plan = data.get("plan", "standard")
    max_students = data.get("max_students", 5000)
    
    if not all([slug, name, subdomain]):
        return jsonify({"error": "Missing required fields: slug, name, subdomain"}), 400
        
    try:
        tenant = TenantService.provision_tenant(
            slug=slug,
            name=name,
            subdomain=subdomain,
            plan=plan,
            max_students=max_students
        )
        return jsonify(status="success", data={
            "tenant": tenant,
            "schema_created": True,
            "migrations_run": True
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@superadmin_bp.route("/tenants/<slug>/config", methods=["PUT"])
def update_tenant_config(slug):
    tenant = qone("SELECT id, subdomain FROM public.tenants WHERE slug = %s", (slug,))
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
        
    data = request.get_json() or {}
    key = data.get("key")
    value = data.get("value")
    
    if not key or value is None:
        return jsonify({"error": "Missing required fields: key, value"}), 400
        
    exe(
        """
        INSERT INTO public.tenant_configs (tenant_id, key, value)
        VALUES (%s, %s, %s)
        ON CONFLICT (tenant_id, key) DO UPDATE SET value = EXCLUDED.value
        """,
        (tenant["id"], key, str(value))
    )
    
    TenantService.bust_cache(tenant["id"], tenant["subdomain"])
    
    exe(
        """
        INSERT INTO public.audit_log (action, tenant_slug, performed_by, payload)
        VALUES ('update_config', %s, 'superadmin', %s)
        """,
        (slug, f"Updated config {key}={value}")
    )
    
    return jsonify(status="success", message="Config updated successfully")

@superadmin_bp.route("/tenants/<slug>/deactivate", methods=["POST"])
def deactivate_tenant(slug):
    tenant = qone("SELECT id, subdomain FROM public.tenants WHERE slug = %s", (slug,))
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
        
    exe("UPDATE public.tenants SET is_active = false WHERE id = %s", (tenant["id"],))
    
    TenantService.bust_cache(tenant["id"], tenant["subdomain"])
    tenant_redis.delete_tenant_all(slug)
    
    exe(
        """
        INSERT INTO public.audit_log (action, tenant_slug, performed_by, payload)
        VALUES ('deactivate_tenant', %s, 'superadmin', 'Tenant deactivated')
        """,
        (slug, 'Tenant deactivated')
    )
    
    return jsonify(status="success", message="Tenant deactivated successfully")

@superadmin_bp.route("/tenants/<slug>/stats", methods=["GET"])
def get_tenant_stats(slug):
    tenant = qone("SELECT id, schema_name FROM public.tenants WHERE slug = %s", (slug,))
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
        
    schema = tenant["schema_name"]
    student_count = 0
    faculty_count = 0
    
    try:
        with get_public_db() as cur:
            cur.execute(f"SET search_path TO {schema}, public")
            cur.execute("SELECT COUNT(*) as count FROM students WHERE is_active = true")
            student_count = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) as count FROM faculty WHERE is_active = true")
            faculty_count = cur.fetchone()["count"]
    except Exception:
        pass
        
    # Estimate storage space on disk
    storage_mb = 0.0
    tenant_dir = os.path.join("/app/uploads", slug)
    if os.path.exists(tenant_dir):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(tenant_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        storage_mb = round(total_size / (1024 * 1024), 2)
        
    last_login_at = datetime.now().isoformat()
    monthly_api_calls = 1250 # Mock metric
    
    return jsonify(status="success", data={
        "student_count": student_count,
        "faculty_count": faculty_count,
        "storage_used_mb": storage_mb,
        "last_login_at": last_login_at,
        "monthly_api_calls": monthly_api_calls
    })

@superadmin_bp.route("/tenants/<slug>/impersonate", methods=["POST"])
def impersonate_tenant(slug):
    tenant = qone("SELECT id, slug, schema_name FROM public.tenants WHERE slug = %s", (slug,))
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
        
    additional_claims = {
        "tenant_id":     tenant['id'],
        "tenant_slug":   tenant['slug'],
        "tenant_schema": tenant['schema_name'],
        "role":          "admin"
    }
    
    access_token = create_access_token(
        identity="impersonated_admin",
        additional_claims=additional_claims,
        expires_delta=timedelta(minutes=15)
    )
    
    client_ip = request.remote_addr or 'unknown'
    exe(
        """
        INSERT INTO public.audit_log (action, tenant_slug, performed_by, ip_address, payload)
        VALUES ('impersonate', %s, 'superadmin', %s, 'Impersonation token generated')
        """,
        (slug, client_ip)
    )
    
    return jsonify(status="success", data={
        "access_token": access_token
    })
