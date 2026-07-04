from flask_smorest import Blueprint

tenant_bp = Blueprint("tenant", __name__, url_prefix="/api/v1/tenant")

from blueprints.tenant import routes
