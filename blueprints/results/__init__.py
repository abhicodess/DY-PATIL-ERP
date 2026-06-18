from flask import Blueprint
results_bp = Blueprint('results', __name__)
from . import routes
