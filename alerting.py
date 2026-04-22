"""
Alerting Utility: Manages external notifications.
"""
import os
import requests
from logging_config import configure_logging

# Initialize a logger specifically for alerts
logger = configure_logging(name="alerting")

def send_alert(message):
    """
    RELIABILITY - ALERTING:
    Sends a live notification to Slack using an Environment Variable.
    """
    logger.error(f"CRITICAL ALERT TRIGGERED: {message}")
    
    WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
    
    if WEBHOOK_URL:
        try:
            slack_payload = {"text": f"*ETL FAILURE* \n{message}"}
            response = requests.post(WEBHOOK_URL, json=slack_payload)
            response.raise_for_status()
            logger.info("Alert successfully sent to Slack.")
        except Exception as e:
            logger.error(f" Failed to send Slack alert: {e}")
    else:
        logger.warning(" SLACK_WEBHOOK_URL not found in environment. Skipping alert.")