"""Teams API endpoints."""
from flask import Blueprint, jsonify

from app.services.transform_service import TransformService

bp = Blueprint("api_teams", __name__, url_prefix="/api")


@bp.route("/teams")
def get_teams():
    """Get team/bowling statistics.
    
    Returns:
        JSON with elite bowlers and team averages
    """
    return jsonify(TransformService.get_teams())
