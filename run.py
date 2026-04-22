"""New modular application entry point.

Usage:
    python run.py           # Run development server
    python run.py --prod    # Run production server with gunicorn
"""
import argparse
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from core.logging_config import configure_logging

logger = configure_logging(__name__)


def run_dev():
    """Run development server."""
    app = create_app()
    logger.info("Starting Flask development server on 0.0.0.0:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)


def run_prod():
    """Run production server with gunicorn."""
    try:
        import gunicorn.app.wsgiapp as wsgi
        
        # Gunicorn configuration
        class AppApplication:
            def __init__(self):
                self.application = create_app()
            
            def run(self):
                wsgi.run(
                    prog="gunicorn",
                    args=[
                        "--bind", "0.0.0.0:5000",
                        "--workers", "4",
                        "--worker-class", "sync",
                        "--timeout", "30",
                        "--access-logfile", "-",
                        "--error-logfile", "-",
                        "--capture-output",
                        "run:app",
                    ]
                )
        
        app = AppApplication()
        app.run()
    except ImportError:
        logger.error("Gunicorn not installed. Run: pip install gunicorn")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cricket Analytics Dashboard")
    parser.add_argument(
        "--prod", "--production",
        action="store_true",
        help="Run in production mode with gunicorn"
    )
    
    args = parser.parse_args()
    
    if args.prod:
        run_prod()
    else:
        run_dev()
