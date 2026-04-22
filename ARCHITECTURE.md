# Project Architecture

This document describes the modular architecture of the Cricket Analytics Dashboard.

## Directory Structure

```
Enterprise_Python_Coding_assignment/
├── app/                          # Web application module
│   ├── __init__.py              # App factory (create_app)
│   ├── extensions.py            # Flask extensions (db, oauth)
│   ├── api/                     # API blueprints
│   │   ├── overview.py          # /api/overview
│   │   ├── matches.py           # /api/matches
│   │   ├── batters.py           # /api/batters
│   │   ├── teams.py             # /api/teams
│   │   ├── chat.py              # /api/chat
│   │   └── logs.py              # /api/logs
│   ├── services/                # Business logic layer
│   │   ├── data_service.py      # Data access from Appwrite
│   │   ├── transform_service.py # Data transformations
│   │   ├── chat_service.py      # AI chatbot
│   │   └── log_service.py       # Log querying
│   └── utils/                   # Shared utilities
│       ├── parsers.py           # Date/int/float parsing
│       └── validators.py        # Input validation
│
├── config/                      # Configuration management
│   └── settings.py              # Pydantic-based settings
│
├── core/                        # Shared core components
│   ├── exceptions.py            # Custom exceptions
│   └── logging_config.py        # Logging setup
│
├── Auth/                        # Authentication (existing)
├── Appwrite/                    # Database client (existing)
├── caching/                     # Redis caching (existing)
├── Logger/                      # Logging (existing)
│
├── etl/                         # ETL Pipeline (refactored from ETL/)
│   ├── extractors/
│   ├── transformers/
│   ├── loaders/
│   └── pipeline.py
│
├── app.py                       # Main entry point (backward compatible)
├── run.py                       # New modular entry point
└── orchestrator.py              # ETL scheduler
```

## Key Design Principles

### 1. Separation of Concerns
- **app/**: Web layer (routes, templates, API)
- **services/**: Business logic (data transformations, AI)
- **config/**: Configuration (env vars, settings)
- **core/**: Shared infrastructure (logging, exceptions)
- **etl/**: Data processing (separate from web app)

### 2. Service Layer Pattern
All business logic lives in services:

```python
from app.services import TransformService, ChatService, DataService

# Get transformed data for UI
data = TransformService.get_overview()

# Get raw data
data = DataService.get_matches()

# AI chat
reply = ChatService.chat(message, history)
```

### 3. Configuration Management
Settings are centralized in `config/settings.py` using Pydantic:

```python
from config import get_settings

settings = get_settings()
print(settings.app_name)
print(settings.gemini_api_key)
```

Benefits:
- Type-safe configuration
- Validation on startup
- Auto-loaded from `.env`
- Singleton pattern (cached)

### 4. Backward Compatibility
- `app.py` remains the main entry point
- All existing routes and functions work unchanged
- New modular imports are available but optional
- Gradual migration path for existing code

## Usage

### Development Server

```bash
# Using the original entry point (still works)
python app.py

# Using the new modular entry point
python run.py

# Production mode
python run.py --prod
```

### Using the App Factory

```python
from app import create_app

app = create_app()
app.run()
```

### Using Services

```python
from app.services import TransformService, DataService

# In a route or other code
overview_data = TransformService.get_overview()
matches = DataService.get_matches()
```

### Using Utilities

```python
from app.utils.parsers import safe_int, DateParser
from app.utils.validators import ChatValidator

# Parse dates
parsed = DateParser.parse_match_date("2024-01-15")

# Safe type conversion
value = safe_int("123", default=0)
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/overview` | GET | Yes | Dashboard overview stats |
| `/api/matches` | GET | Yes | Match list with filters |
| `/api/batters` | GET | Yes | Batting leaderboard |
| `/api/teams` | GET | Yes | Team/bowling stats |
| `/api/chat` | POST | Yes | AI chatbot |
| `/api/logs` | GET | Admin | Query application logs |
| `/health` | GET | No | Health check |

## Migration Guide

### For existing code in app.py:
No changes needed. The existing code continues to work.

### For new features:
Prefer importing from the modular structure:

```python
# New way (preferred)
from app.services import TransformService
from app.utils.parsers import safe_int
from config import get_settings

# Instead of duplicating code in app.py
def my_new_route():
    data = TransformService.get_overview()
    return jsonify(data)
```

### For new files/modules:
Place them in the appropriate directory:
- New API endpoints → `app/api/`
- New business logic → `app/services/`
- New utilities → `app/utils/`
- New config → `config/`

## Testing

```bash
# Syntax check
python -m py_compile app/services/transform_service.py

# Import check
python -c "from app.services import TransformService; print('OK')"

# Run app
python run.py
```

## Future Improvements

1. **ETL Modularization**: The ETL pipeline can be further split into extractors/transformers/loaders
2. **Testing**: Add `tests/` directory with pytest
3. **API Documentation**: Add OpenAPI/Swagger generation
4. **Async**: Consider async database calls for better performance
5. **Migrations**: Add Alembic for database schema management
