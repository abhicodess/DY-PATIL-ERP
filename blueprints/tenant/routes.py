from flask import jsonify
from blueprints.tenant import tenant_bp
from utils.tenant_context import get_current_tenant

@tenant_bp.route("/info", methods=["GET"])
def get_tenant_info():
    try:
        tenant = get_current_tenant()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
        
    return jsonify(status="success", data={
        "name": tenant["name"],
        "slug": tenant["slug"],
        "subdomain": tenant["subdomain"],
        "primary_color": tenant.get("primary_color", "#800000"),
        "logo_url": tenant.get("custom_logo"),
        "plan": tenant.get("plan", "standard")
    })
