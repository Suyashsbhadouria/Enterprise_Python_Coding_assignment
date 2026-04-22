"""Data parsing utilities."""
from datetime import datetime, date
from typing import Optional, List
from config.settings import get_settings


class DateParser:
    """Parse dates in various formats."""
    
    @staticmethod
    def parse_match_date(value: str) -> datetime:
        """Parse supported date formats and return a sortable datetime."""
        if not value:
            return datetime.min
        
        settings = get_settings()
        
        for date_format in settings.date_formats:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
        
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.min
    
    @staticmethod
    def parse_log_datetime(value: str, *, end_of_day: bool = False) -> Optional[datetime]:
        """Parse date/datetime filters accepted by /api/logs endpoint."""
        if not value:
            return None
        
        raw = value.strip()
        settings = get_settings()
        
        for fmt in settings.log_date_formats:
            try:
                parsed = datetime.strptime(raw, fmt)
                if fmt == "%Y-%m-%d" and end_of_day:
                    parsed = parsed.replace(hour=23, minute=59, second=59)
                return parsed
            except ValueError:
                continue
        
        try:
            normalized = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError:
            return None


class LogParser:
    """Parse log file entries."""
    
    @staticmethod
    def parse_log_line(raw_line: str, timestamp_format: str = None) -> Optional[dict]:
        """Parse one formatted log line into a structured entry."""
        parts = raw_line.rstrip("\n").split(" | ", 3)
        if len(parts) != 4:
            return None
        
        timestamp_str, level, logger_name, message = parts
        settings = get_settings()
        fmt = timestamp_format or settings.log_line_timestamp_format
        
        try:
            timestamp = datetime.strptime(timestamp_str, fmt)
        except ValueError:
            return None
        
        return {
            "timestamp": timestamp_str,
            "level": level,
            "logger": logger_name,
            "message": message,
            "_dt": timestamp,
        }


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
