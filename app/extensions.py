"""Flask extensions initialized here to avoid circular imports.

Extensions are initialized without the app, then bound to it
in the application factory.
"""
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth

# Initialize extensions
db = SQLAlchemy()
oauth = OAuth()
