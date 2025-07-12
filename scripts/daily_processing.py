#!/usr/bin/env python3
"""
Daily processing script to:
1. Extract new recordings from Zoom
2. Process recordings in Google Drive
3. Update the Zoom report with insight URLs
4. Send email notifications

This script is designed to be run daily via cron.
"""

import os
import sys
import json
import logging
import argparse
import smtplib
import asyncio
import subprocess
import glob
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from the app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import config

# Set up logging
log_dir = os.path.join(parent_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"daily_processing_{datetime.now().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def send_notification_email(subject: str, body: str) -> bool:
    """
    Send a notification email.
    
    Args:
        subject: Email subject
        body: Email body
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    # Load environment variables
    load_dotenv()
    
    # Get email settings
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    sender_email = os.environ.get("SENDER_EMAIL")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    
    if not all([smtp_server, smtp_username, smtp_password, sender_email, recipient_email]):
        logger.error("Email settings not configured. Skipping notification.")
        return False
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        
        # Add body
        message.attach(MIMEText(body, "plain"))
        
        # Connect to server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        
        logger.info(f"Email notification sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        return False

def run_script(script_path: str, args: List[str] = None) -> bool:
    """
    Run a Python script and return whether it was successful.
    
    Args:
        script_path: Path to the script
        args: List of command-line arguments
        
    Returns:
        True if script ran successfully, False otherwise
    """
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    logger.info(f"Running script: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        logger.info(f"Script output: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False

def rotate_logs(days_to_keep=30):
    """
    Delete log files older than the specified number of days.
    
    Args:
        days_to_keep: Number of days of logs to keep
    """
    log_dir = os.path.join(parent_dir, "logs")
    
    if not os.path.exists(log_dir):
        logger.warning(f"Log directory not found: {log_dir}")
        return
    
    # Get all daily processing log files
    log_pattern = os.path.join(log_dir, "daily_processing_*.log")
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        logger.debug("No log files to rotate.")
        return
    
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Track deleted files
    deleted_files = 0
    
    for log_file in log_files:
        # Extract date from filename
        try:
            filename = os.path.basename(log_file)
            date_str = filename.replace("daily_processing_", "").replace(".log", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Delete if older than cutoff
            if file_date < cutoff_date:
                os.remove(log_file)
                deleted_files += 1
                
        except (ValueError, Exception) as e:
            logger.error(f"Error processing {log_file}: {e}")
    
    if deleted_files > 0:
        logger.info(f"Log rotation complete: {deleted_files} files deleted.")

async def daily_processing():
    """Run the daily processing workflow."""
    start_time = datetime.now()
    logger.info(f"Starting daily processing at {start_time}")
    
    # Rotate logs first (keep last 30 days)
    rotate_logs(30)
    
    # Results tracking
    results = {
        "extract_historical": False,
        "process_drive": False,
        "update_urls": False,
        "sessions_processed": 0,
        "errors": []
    }
    
    try:
        # 1. Extract historical recordings from yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        extract_script = os.path.join(parent_dir, "scripts", "extract_historical_recordings.py")
        extract_args = [
            "--start-date", yesterday,
            "--end-date", yesterday,
            "--temp-dir", os.path.join(parent_dir, "temp"),
            "--log-level", "INFO"
        ]
        
        results["extract_historical"] = run_script(extract_script, extract_args)
        
        # 2. Process recordings in Google Drive
        process_script = os.path.join(parent_dir, "scripts", "process_drive_recordings.py")
        process_args = [
            "--temp-dir", os.path.join(parent_dir, "temp"),
            "--log-level", "INFO",
            "--backoff-time", "120"
        ]
        
        results["process_drive"] = run_script(process_script, process_args)
        
        # 3. Update the Zoom report with insight URLs
        update_script = os.path.join(parent_dir, "update_insight_urls.py")
        results["update_urls"] = run_script(update_script)
        
        # 4. Check for sessions with missing insights
        check_script = os.path.join(parent_dir, "check_entries_with_insights.py")
        run_script(check_script)
        
    except Exception as e:
        error_msg = f"Error in daily processing: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    # Calculate processing time
    end_time = datetime.now()
    processing_time = end_time - start_time
    
    # Prepare email notification
    status = "SUCCESS" if all([results["extract_historical"], results["process_drive"], results["update_urls"]]) else "PARTIAL SUCCESS" if any([results["extract_historical"], results["process_drive"], results["update_urls"]]) else "FAILURE"
    
    subject = f"Zoom Insights Daily Processing: {status} ({datetime.now().strftime('%Y-%m-%d')})"
    
    body = f"""
Zoom Insights Daily Processing Report
====================================

Date: {datetime.now().strftime('%Y-%m-%d')}
Status: {status}
Processing Time: {processing_time}

Steps:
1. Extract Historical Recordings: {"SUCCESS" if results["extract_historical"] else "FAILURE"}
2. Process Drive Recordings: {"SUCCESS" if results["process_drive"] else "FAILURE"}
3. Update Insight URLs: {"SUCCESS" if results["update_urls"] else "FAILURE"}

For detailed logs, see: {log_file}

{"Errors:" if results["errors"] else ""}
{chr(10).join(results["errors"]) if results["errors"] else ""}
"""
    
    # Send email notification
    send_notification_email(subject, body)
    
    logger.info(f"Daily processing completed in {processing_time}")
    logger.info(f"Status: {status}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily processing of Zoom recordings")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Set logging level")
    
    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    asyncio.run(daily_processing()) 