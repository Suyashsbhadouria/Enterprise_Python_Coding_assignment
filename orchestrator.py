"""
Orchestrator Utility: Manages Scheduling & Reliability for the ETL Pipeline.
This acts as the "Control Plane" for the application.
"""

import os
import time
import glob
import schedule
import requests  # <-- ADDED: Needed to send the webhook to Slack

# 1. Import your team's custom logger
from logging_config import configure_logging

# 2. Import the main pipeline function from your actual ETL file
from etl_pipeline import run_pipeline, DATASET_DIR

# 3. Initialize the logger specifically for the orchestrator
logger = configure_logging(name="orchestrator")


def check_upstream_data():
    """
    RELIABILITY - SENSOR: 
    Checks if the dataset directory has files before attempting extraction.
    Prevents the pipeline from running and creating empty CSVs if data is delayed.
    """
    json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))
    if not json_files:
        error_msg = "⚠️ *UPSTREAM DATA MISSING*: No JSON files found in the dataset directory. ETL cycle aborted."
        logger.warning(error_msg)
        
        # 👇 ADD THIS LINE TO FIRE THE ALERT TO SLACK 👇
        send_alert(error_msg) 
        
        return False
    return True


def send_alert(message):
    """
    RELIABILITY - ALERTING:
    Sends a live notification to Slack using an Environment Variable.
    """
    logger.error(f"🚨 CRITICAL ALERT TRIGGERED: {message}")
    
    # This pulls the URL from your computer's settings, not the code!
    WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
    
    if WEBHOOK_URL:
        try:
            slack_payload = {"text": f"🚨 *ETL FAILURE* 🚨\n{message}"}
            response = requests.post(WEBHOOK_URL, json=slack_payload)
            response.raise_for_status()
            logger.info("✅ Alert successfully sent to Slack.")
        except Exception as e:
            logger.error(f"❌ Failed to send Slack alert: {e}")
    else:
        logger.warning("⚠️ SLACK_WEBHOOK_URL not found in environment. Skipping alert.")

def execute_with_reliability(max_retries=3, delay=5):
    """
    RELIABILITY - RETRIES:
    Wraps the ETL function call in an exponential backoff loop.
    """
    logger.info("Starting scheduled ETL cycle...")
    
    # 1. Check for late upstream data first
    if not check_upstream_data():
        logger.info("Aborting this cycle. Will wait for the next scheduled run.")
        return

    # 2. Execute with Retry Logic
    attempt = 1
    while attempt <= max_retries:
        try:
            logger.info(f"Triggering ETL Pipeline (Attempt {attempt}/{max_retries})...")
            
            # --- THE FUNCTION CALL TO YOUR TEAM'S CODE ---
            run_pipeline()  
            
            logger.info("✅ ETL cycle completed successfully.")
            return  # Exit function immediately on success
            
        except Exception as e:
            logger.warning(f"⚠️ Execution failed on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            attempt += 1

    # 3. Alert if all retries are exhausted
    send_alert(f"Pipeline failed completely after {max_retries} attempts.")


def start_scheduler():
    """
    SCHEDULING:
    Controls when the reliable execution function runs.
    """
    logger.info("Starting Enterprise Orchestrator...")
    
    # Schedule the job. 
    schedule.every(10).minutes.do(execute_with_reliability)
    
    # Run once immediately on startup
    execute_with_reliability()

    # Keep the script running to check the schedule
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduler()
    # send_alert("🚀 MANUAL TEST: The Slack integration is working perfectly!")