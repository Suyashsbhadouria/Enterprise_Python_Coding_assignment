"""Logs API endpoints."""
from flask import Blueprint, jsonify, request

from app.services.log_service import LogService
from app.utils.parsers import DateParser
from core.logging_config import get_log_file_path
from Auth.auth import admin_required

bp = Blueprint("api_logs", __name__, url_prefix="/api")


@bp.route("/logs")
@admin_required
def get_logs():
    """Query log entries with filtering.
    
    Query Parameters:
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        limit: Maximum entries to return (1-2000, default 200)
        q: Text search query
        since: Filter entries after this datetime (YYYY-MM-DD or ISO format)
        until: Filter entries before this datetime
        include_archived: Include rotated log files (true/false)
        
    Returns:
        JSON with filtered log entries and metadata
    """
    # Validate level
    level = request.args.get("level", "").strip().upper()
    is_valid, error_msg = LogService.VALID_LOG_LEVELS, None
    if level and level not in LogService.VALID_LOG_LEVELS:
        return jsonify({
            "error": f"Invalid level. Use one of: {', '.join(sorted(LogService.VALID_LOG_LEVELS))}"
        }), 400
    
    # Validate limit
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        return jsonify({"error": "Invalid limit. Provide an integer between 1 and 2000."}), 400
    
    limit = max(1, min(limit, 2000))
    
    # Parse other parameters
    query = request.args.get("q", "").strip()
    since_raw = request.args.get("since", "").strip()
    until_raw = request.args.get("until", "").strip()
    include_archived = request.args.get("include_archived", "false").strip().lower() in {"1", "true", "yes"}
    
    # Parse datetime filters
    since = DateParser.parse_log_datetime(since_raw)
    until = DateParser.parse_log_datetime(until_raw, end_of_day=True)
    
    # Validate datetime range
    if since_raw and since is None:
        return jsonify({
            "error": "Invalid since value. Use YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, or ISO datetime."
        }), 400
    
    if until_raw and until is None:
        return jsonify({
            "error": "Invalid until value. Use YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, or ISO datetime."
        }), 400
    
    if since and until and since > until:
        return jsonify({"error": "Invalid range. 'since' must be earlier than or equal to 'until'."}), 400
    
    # Query logs
    entries, source_files = LogService.query_entries(
        limit=limit,
        level=level,
        query=query,
        since=since,
        until=until,
        include_archived=include_archived
    )
    
    return jsonify({
        "log_file": get_log_file_path(),
        "source_files": source_files,
        "filters": {
            "level": level or None,
            "q": query or None,
            "since": since_raw or None,
            "until": until_raw or None,
            "limit": limit,
            "include_archived": include_archived,
        },
        "returned": len(entries),
        "entries": entries,
    })
