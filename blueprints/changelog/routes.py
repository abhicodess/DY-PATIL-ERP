from flask import jsonify
from flask_smorest import Blueprint
from api.changelog_data import CHANGELOG_DATA

changelog_bp = Blueprint(
    'changelog', __name__, url_prefix='/api/changelog',
    description="API Changelog endpoints"
)

@changelog_bp.route('', methods=['GET'])
@changelog_bp.doc(
    summary="Get API changelog",
    description="Returns the full machine-readable release history and migration guide links.",
    tags=["Changelog"]
)
def get_changelog():
    return jsonify(CHANGELOG_DATA)
