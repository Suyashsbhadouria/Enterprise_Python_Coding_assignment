"""
Orchestrator Utility: Manages Scheduling & Reliability for the ETL Pipeline.
This acts as the "Control Plane" for the application.
"""

import os
import time
import glob
import schedule

# 1. Import your custom logger
from logging_config import configure_logging

# 2. Import the main pipeline function
from etl_pipeline import run_pipeline, DATASET_DIR

# 3. IMPORT YOUR NEW ALERTING MODULE 👇
from alerting import send_alert

# 4. Initialize the logger
logger = configure_logging(name="orchestrator")


def check_upstream_data():
    """
    RELIABILITY - SENSOR: 
    Checks if the dataset directory has files before attempting extraction.
    """
    json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))
    if not json_files:
        error_msg = "⚠️ *UPSTREAM DATA MISSING*: No JSON files found in the dataset directory. ETL cycle aborted."
        logger.warning(error_msg)
        
        send_alert(error_msg) 
        
        return False
    return True


def execute_with_reliability(max_retries=3, delay=5):
    """
    RELIABILITY - RETRIES:
    Wraps the ETL function call in an exponential backoff loop.
    """
    logger.info("Starting scheduled ETL cycle...")
    
    if not check_upstream_data():
        logger.info("Aborting this cycle. Will wait for the next scheduled run.")
        return

    attempt = 1
    while attempt <= max_retries:
        try:
            logger.info(f"Triggering ETL Pipeline (Attempt {attempt}/{max_retries})...")
            
            run_pipeline()  
            
            logger.info("✅ ETL cycle completed successfully.")
            return  
            
        except Exception as e:
            logger.warning(f"⚠️ Execution failed on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            attempt += 1

    send_alert(f"Pipeline failed completely after {max_retries} attempts.")


def start_scheduler():
    """
    SCHEDULING:
    Controls when the reliable execution function runs.
    """
    logger.info("Starting Enterprise Orchestrator...")
    schedule.every(10).minutes.do(execute_with_reliability)
    execute_with_reliability()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduler()