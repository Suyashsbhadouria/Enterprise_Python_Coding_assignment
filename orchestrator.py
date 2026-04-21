"""
Orchestrator Utility: Manages Scheduling & Reliability for the ETL Pipeline.
This acts as the "Control Plane" for the application.
"""

import os
import time
import glob
import schedule

# 1. Import your team's custom logger
from logging_config import configure_logging

# 2. Import the main pipeline function from your actual ETL file
from etl_pipeline import run_pipeline, DATASET_DIR

# 3. Initialize the logger specifically for the orchestrator
# Passing "orchestrator" renames the tag in the log file so you know who is talking
logger = configure_logging(name="orchestrator")


def check_upstream_data():
    """
    RELIABILITY - SENSOR: 
    Checks if the dataset directory has files before attempting extraction.
    Prevents the pipeline from running and creating empty CSVs if data is delayed.
    """
    json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))
    if not json_files:
        logger.warning("Upstream data not ready. No JSON files found in dataset directory.")
        return False
    return True


def send_alert(message):
    """
    RELIABILITY - ALERTING:
    Triggers when the pipeline completely fails. 
    In production, this would send a Slack/Teams webhook or an email.
    """
    logger.error(f"🚨 CRITICAL ALERT TRIGGERED: {message}")
    # Example: requests.post(WEBHOOK_URL, json={"text": message})


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
    send_alert("ETL Pipeline failed completely after exhausting all retries.")


def start_scheduler():
    """
    SCHEDULING:
    Controls when the reliable execution function runs.
    """
    logger.info("Starting Enterprise Orchestrator...")
    
    # Schedule the job. 
    # For production it might look like: schedule.every().day.at("02:00").do(execute_with_reliability)
    # For your testing right now, it runs every 10 minutes:
    schedule.every(10).minutes.do(execute_with_reliability)
    
    # Run once immediately on startup so you don't have to wait 10 mins to test it
    execute_with_reliability()

    # Keep the script running to check the schedule
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduler()