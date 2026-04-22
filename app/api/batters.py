"""Batters API endpoints."""
from flask import Blueprint, jsonify

from app.services.transform_service import TransformService

bp = Blueprint("api_batters", __name__, url_prefix="/api")


@bp.route("/batters")
def get_batters():
    """Get batting statistics.
    
    Returns:
        JSON with batting leaderboard and scoring metrics
    """
    return jsonify(TransformService.get_batters())
