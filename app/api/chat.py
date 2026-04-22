"""Chatbot API endpoints."""
from flask import Blueprint, jsonify, request

from app.services.chat_service import ChatService
from app.utils.validators import get_chat_validator
from config.settings import get_settings

bp = Blueprint("api_chat", __name__, url_prefix="/api")


@bp.route("/chat", methods=["POST"])
def chat():
    """Process a chat message and return AI response.
    
    Request Body:
        message: User's question
        history: Previous conversation turns (optional)
        
    Returns:
        JSON with AI reply or error
    """
    settings = get_settings()
    payload = request.get_json(silent=True) or {}
    
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    
    if not isinstance(history, list):
        history = []
    
    # Validate message
    if not message:
        return jsonify({"error": "Message is required."}), 400
    
    # Check message length
    if len(message) > settings.chat_max_message_length:
        message = message[:settings.chat_max_message_length]
    
    # Validate cricket query
    validator = get_chat_validator()
    is_valid, error_msg, _ = validator.validate_message(message)
    
    if not is_valid:
        return jsonify({"reply": error_msg})
    
    # Check API key
    if not settings.gemini_api_key:
        return jsonify({
            "reply": (
                "Gemini API key is not configured yet. "
                "Set GEMINI_API_KEY in your environment, then ask a cricket question again."
            )
        })
    
    # Call chat service
    reply = ChatService.chat(message, history)
    
    if not reply:
        reply = settings.chat_decline_message
    
    return jsonify({"reply": reply})
