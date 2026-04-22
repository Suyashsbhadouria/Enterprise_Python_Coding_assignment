"""Overview API endpoints."""
from flask import Blueprint, jsonify

from app.services.transform_service import TransformService
from Auth.auth import admin_required

bp = Blueprint("api_overview", __name__, url_prefix="/api")


@bp.route("/overview")
def get_overview():
    """Get overview dashboard data.
    
    Returns:
        JSON with total matches, runs, team stats, etc.
    """
    return jsonify(TransformService.get_overview())
