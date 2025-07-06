#!/usr/bin/env python
"""
Script to extract meeting passwords from Zoom recordings and update the report.
This script will:
1. Read the Zoom recordings report
2. For each recording, check if the password is missing
3. If missing, fetch the recording details from Zoom API
4. Extract the password and update the report
"""

import os
import sys
import json
import logging
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"password_extraction_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_filename}")

class ZoomClient:
    """Class for interacting with Zoom API."""
    
    def __init__(self):
        """Initialize the Zoom client."""
        self.client_id = config.ZOOM_CLIENT_ID
        self.client_secret = config.ZOOM_CLIENT_SECRET
        self.account_id = config.ZOOM_ACCOUNT_ID
        self.base_url = config.ZOOM_BASE_URL
        self.access_token = None
        self.token_expiry = 0
        
        logger.info("Zoom Configuration:")
        logger.info(f"Client ID: {self.client_id[:5]}*******{self.client_id[-4:]}")
        logger.info(f"Client Secret: ********")
        logger.info(f"Account ID: {self.account_id[:5]}*******{self.account_id[-4:]}")
        logger.info(f"Base URL: {self.base_url}")
    
    def get_access_token(self) -> str:
        """
        Get an access token from Zoom API.
        
        Returns:
            Access token
        """
        # Check if we already have a valid token
        now = datetime.now().timestamp()
        if self.access_token and now < self.token_expiry:
            return self.access_token
            
        # Request a new token
        url = "https://zoom.us/oauth/token"
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }
        
        logger.info(f"Requesting access token from {url}")
        logger.info(f"Request data: {json.dumps(data)}")
        
        response = requests.post(url, auth=auth, data=data)
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Failed to get access token: {response.text}")
            raise Exception(f"Failed to get access token: {response.text}")
            
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expiry = now + data["expires_in"] - 60  # Subtract 60 seconds for safety
        
        logger.info(f"Access token received")
        logger.info(f"Token type: {data['token_type']}")
        logger.info(f"Expires in: {data['expires_in']} seconds")
        logger.info(f"OAuth scopes received (use --log-level=DEBUG to see full scopes)")
        
        return self.access_token
    
    def get_recording_details(self, meeting_id: str, meeting_uuid: str = None) -> Dict:
        """
        Get recording details from Zoom API.
        
        Args:
            meeting_id: Meeting ID
            meeting_uuid: Meeting UUID (optional)
            
        Returns:
            Recording details
        """
        # Try with meeting_uuid first if provided
        if meeting_uuid:
            try:
                # Clean up UUID (remove '=' padding)
                clean_uuid = meeting_uuid.rstrip('=')
                url = f"{self.base_url}/meetings/{clean_uuid}/recordings"
                headers = {
                    "Authorization": f"Bearer {self.get_access_token()}",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Getting recording details for meeting UUID: {clean_uuid}")
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get recording with UUID: {response.text}")
            except Exception as e:
                logger.warning(f"Error getting recording with UUID: {e}")
        
        # Fall back to meeting_id
        try:
            url = f"{self.base_url}/meetings/{meeting_id}/recordings"
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Getting recording details for meeting ID: {meeting_id}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get recording: {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Error getting recording: {e}")
            return {}
    
    def get_user(self, user_id: str) -> Dict:
        """
        Get user details from Zoom API.
        
        Args:
            user_id: User ID
            
        Returns:
            User details
        """
        url = f"{self.base_url}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting user details for {user_id}")
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get user details: {response.text}")
                return {}
        except Exception as e:
            logger.warning(f"Error getting user details: {e}")
            return {}

def update_zoom_report(temp_dir: str):
    """
    Update the Zoom report with meeting passwords and host information.
    
    Args:
        temp_dir: Directory for temporary files
    """
    try:
        # Check if report exists
        report_path = os.path.join(temp_dir, "zoom_recordings_report.csv")
        if not os.path.exists(report_path):
            logger.warning(f"Zoom report not found at {report_path}")
            return
        
        # Read the report
        df = pd.read_csv(report_path)
        
        # Initialize Zoom client
        zoom_client = ZoomClient()
        
        # Track updates
        password_updates = 0
        host_updates = 0
        
        # Process each row
        for i, row in df.iterrows():
            meeting_id = row.get("Meeting ID")
            meeting_uuid = row.get("Meeting UUID")
            
            # Skip if no meeting ID or UUID
            if not meeting_id or pd.isna(meeting_id):
                continue
                
            # Check if password is missing
            if pd.isna(row.get("Meeting Password")) or row.get("Meeting Password") == "":
                logger.info(f"Fetching password for meeting ID: {meeting_id}")
                
                # Get recording details
                recording = zoom_client.get_recording_details(str(meeting_id), str(meeting_uuid))
                
                # Extract password
                password = recording.get("password", "")
                if password:
                    df.at[i, "Meeting Password"] = password
                    password_updates += 1
                    logger.info(f"Updated password for meeting: {row['Meeting Topic']}")
                
                # Check if host information is missing
                if row.get("Host Name") == "Unknown" or row.get("Host Email") == "Unknown":
                    host_id = recording.get("host_id", "")
                    if host_id:
                        user_details = zoom_client.get_user(host_id)
                        if user_details:
                            df.at[i, "Host Name"] = f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}"
                            df.at[i, "Host Email"] = user_details.get("email", "Unknown")
                            host_updates += 1
                            logger.info(f"Updated host information for meeting: {row['Meeting Topic']}")
        
        if password_updates > 0 or host_updates > 0:
            # Save the updated report
            df.to_csv(report_path, index=False)
            logger.info(f"Saved updated report with {password_updates} password updates and {host_updates} host information updates")
            
            # Upload to Google Drive
            credentials = service_account.Credentials.from_service_account_file(
                config.GOOGLE_CREDENTIALS_FILE, 
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            drive_service = build("drive", "v3", credentials=credentials)
            
            report_name = "Zoom Recordings Report"
            query = f"name = '{report_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{config.GOOGLE_DRIVE_ROOT_FOLDER}' in parents and trashed = false"
            results = drive_service.files().list(q=query).execute()
            
            if results.get('files'):
                file_id = results['files'][0]['id']
                
                # Create media
                media = MediaFileUpload(
                    report_path,
                    mimetype='text/csv',
                    resumable=True
                )
                
                # Update file content
                logger.info(f"Updating existing report with ID: {file_id}")
                file = drive_service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                
                # Get the webViewLink
                file = drive_service.files().get(
                    fileId=file_id,
                    fields='webViewLink'
                ).execute()
                
                logger.info(f"Report updated successfully")
                logger.info(f"Report can be viewed at: {file.get('webViewLink')}")
        else:
            logger.info("No changes made to the report")
    except Exception as e:
        logger.error(f"Error updating Zoom report: {e}")

def main():
    """Main function to extract meeting passwords."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract meeting passwords from Zoom recordings")
    parser.add_argument("--temp-dir", type=str, default="./temp", help="Temporary directory for downloads")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="Set the logging level")
    
    args = parser.parse_args()
    
    # Set logging level based on command-line argument
    logger.setLevel(getattr(logging, args.log_level))
    
    # Create temp directory
    os.makedirs(args.temp_dir, exist_ok=True)
    
    logger.info("Starting password extraction")
    
    # Update the Zoom report with meeting passwords
    update_zoom_report(args.temp_dir)
    
    logger.info("Password extraction completed")

if __name__ == "__main__":
    main() 