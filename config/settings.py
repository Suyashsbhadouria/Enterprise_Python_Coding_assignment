"""Centralized configuration management using Pydantic.

This module provides type-safe, validated configuration for the application.
All settings are loaded from environment variables with sensible defaults.
"""
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App metadata
    app_name: str = Field(default="BoundaryLine Intelligence", alias="APP_NAME")
    
    # Flask settings
    flask_secret_key: str = Field(alias="FLASK_SECRET_KEY")
    sqlalchemy_database_uri: str = Field(default="sqlite:///users.db", alias="SQLALCHEMY_DATABASE_URI")
    
    # Logging settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_file_name: str = Field(default="app.log", alias="LOG_FILE_NAME")
    log_max_bytes: int = Field(default=1048576, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    
    # Appwrite settings
    appwrite_endpoint: str = Field(alias="APPWRITE_ENDPOINT")
    appwrite_api_key: str = Field(alias="APPWRITE_API_KEY")
    appwrite_project_id: str = Field(alias="APPWRITE_PROJECT_ID")
    appwrite_database_id: str = Field(alias="APPWRITE_DATABASE_ID")
    appwrite_matches_collection_id: str = Field(default="matches", alias="APPWRITE_MATCHES_COLLECTION_ID")
    appwrite_batting_collection_id: str = Field(default="batting", alias="APPWRITE_BATTING_COLLECTION_ID")
    appwrite_bowling_collection_id: str = Field(default="bowling", alias="APPWRITE_BOWLING_COLLECTION_ID")
    
    # OAuth settings
    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(alias="GOOGLE_CLIENT_SECRET")
    
    # Redis settings
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    # Gemini AI settings
    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_MODEL")
    gemini_max_tokens: int = Field(default=320)
    gemini_temperature: float = Field(default=0.1)
    gemini_top_k: int = Field(default=32)
    gemini_top_p: float = Field(default=0.9)
    
    # Chatbot settings
    chat_decline_message: str = Field(
        default="I can only answer cricket questions using this dashboard dataset.",
        alias="CHAT_DECLINE_MESSAGE"
    )
    chat_max_history: int = Field(default=6)
    chat_max_message_length: int = Field(default=1200)
    
    # Alerting settings
    slack_webhook_url: Optional[str] = Field(default=None, alias="SLACK_WEBHOOK_URL")
    
    # Date formats for parsing
    date_formats: List[str] = Field(
        default=["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]
    )
    log_date_formats: List[str] = Field(
        default=["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    )
    log_line_timestamp_format: str = Field(default="%Y-%m-%d %H:%M:%S")
    
    # Cache settings
    cache_ttl_overview: int = Field(default=300)  # 5 minutes
    cache_ttl_batters: int = Field(default=300)
    cache_ttl_teams: int = Field(default=300)
    
    # ETL settings
    etl_dataset_dir: str = Field(default="Dataset/Raw")
    etl_output_dir: str = Field(default="etl/csv_data")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance.
    
    Uses singleton pattern to avoid reloading .env on every call.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Force reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings
