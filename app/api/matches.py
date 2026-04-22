"""Matches API endpoints."""
from flask import Blueprint, jsonify, request

from app.services.transform_service import TransformService

bp = Blueprint("api_matches", __name__, url_prefix="/api")


@bp.route("/matches")
def get_matches():
    """Get match data with optional filtering.
    
    Query Parameters:
        city: Filter by city name
        team: Filter by team name
        
    Returns:
        JSON with match history and venue statistics
    """
    city = request.args.get("city", "All Cities")
    team = request.args.get("team", "All Teams")
    return jsonify(TransformService.get_matches(city, team))
