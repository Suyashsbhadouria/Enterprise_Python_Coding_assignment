"""Custom application exceptions."""


class AppError(Exception):
    """Base application exception."""
    
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AppError):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=500, details=details)


class DataSourceError(AppError):
    """Raised when data source (Appwrite) fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)


class ValidationError(AppError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(AppError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required", details: dict = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(AppError):
    """Raised when user lacks permissions."""
    
    def __init__(self, message: str = "Access forbidden", details: dict = None):
        super().__init__(message, status_code=403, details=details)


class ChatServiceError(AppError):
    """Raised when chat/AI service fails."""
    
    def __init__(self, message: str = "Chat service unavailable", details: dict = None):
        super().__init__(message, status_code=503, details=details)
