#!/usr/bin/env python3
"""
Script to update missing metadata for sessions in the Zoom Report.

This script:
1. Reads the current Zoom Report
2. Identifies sessions with missing metadata
3. Uses the Zoom API to fetch the missing information
4. Updates the report with the complete metadata
"""

import os
import sys
import json
import logging
import asyncio
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ZoomClient:
    """Client for interacting with Zoom API."""
    
    def __init__(self):
        """Initialize the Zoom client."""
        # Load environment variables
        load_dotenv()
        
        self.client_id = os.environ.get("ZOOM_CLIENT_ID")
        self.client_secret = os.environ.get("ZOOM_CLIENT_SECRET")
        self.account_id = os.environ.get("ZOOM_ACCOUNT_ID")
        self.base_url = os.environ.get("ZOOM_API_BASE_URL", "https://api.zoom.us/v2")
        
        if not all([self.client_id, self.client_secret, self.account_id]):
            raise ValueError("Missing required Zoom API credentials")
        
        logger.info("Zoom Configuration:")
        logger.info(f"Client ID: {self.client_id[:5]}*************{self.client_id[-4:]}")
        logger.info(f"Client Secret: ********")
        logger.info(f"Account ID: {self.account_id[:5]}*************{self.account_id[-4:]}")
        logger.info(f"Base URL: {self.base_url}")
        
        self.access_token = None
        self.token_expires_at = datetime.now()
    
    def get_access_token(self) -> str:
        """
        Get an access token from the Zoom API.
        
        Returns:
            Access token string
        """
        # Check if we have a valid token
        if self.access_token and datetime.now() < self.token_expires_at:
            return self.access_token
        
        # Get a new token
        logger.info("Requesting access token from https://zoom.us/oauth/token")
        
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }
        
        logger.info(f"Request data: {json.dumps(data)}")
        
        response = requests.post(
            "https://zoom.us/oauth/token",
            auth=auth,
            data=data
        )
        
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Failed to get access token: {response.text}")
            raise Exception(f"Failed to get access token: {response.text}")
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"] - 60)
        
        logger.info("Access token received")
        logger.info(f"Token type: {token_data['token_type']}")
        logger.info(f"Expires in: {token_data['expires_in']} seconds")
        logger.info("OAuth scopes received (use --log-level=DEBUG to see full scopes)")
        
        return self.access_token
    
    def get_meeting_details(self, meeting_id: str) -> Dict:
        """
        Get details for a specific meeting.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            Meeting details as a dictionary
        """
        token = self.get_access_token()
        url = f"{self.base_url}/meetings/{meeting_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting meeting details for meeting ID: {meeting_id}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get meeting details: {response.text}")
            return {}
        
        return response.json()
    
    def get_recording_details(self, meeting_uuid: str) -> Dict:
        """
        Get recording details for a specific meeting.
        
        Args:
            meeting_uuid: The meeting UUID
            
        Returns:
            Recording details as a dictionary
        """
        token = self.get_access_token()
        url = f"{self.base_url}/meetings/{meeting_uuid}/recordings"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting recording details for meeting UUID: {meeting_uuid}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get recording details: {response.text}")
            return {}
        
        return response.json()
    
    def get_user(self, user_id: str) -> Dict:
        """
        Get details for a specific user.
        
        Args:
            user_id: The user ID
            
        Returns:
            User details as a dictionary
        """
        token = self.get_access_token()
        url = f"{self.base_url}/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting user details for user ID: {user_id}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get user details: {response.text}")
            return {}
        
        return response.json()

def get_drive_service():
    """
    Get a Google Drive service instance.
    
    Returns:
        Google Drive service instance
    """
    credentials = service_account.Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    )
    
    return build("drive", "v3", credentials=credentials)

def get_sheets_service():
    """
    Get a Google Sheets service instance.
    
    Returns:
        Google Sheets service instance
    """
    credentials = service_account.Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    
    return build("sheets", "v4", credentials=credentials)

async def update_session_metadata():
    """Update missing metadata for sessions in the Zoom Report."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    logger.info(f"Updating metadata in Zoom Report with ID: {report_id}")
    
    # Initialize Zoom client
    zoom_client = ZoomClient()
    
    # Initialize Google Sheets service
    sheets_service = get_sheets_service()
    
    # Get sheet names first
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        sys.exit(1)
        
    # Use the first sheet's title
    sheet_title = sheets[0]['properties']['title']
    logger.info(f"Using sheet: {sheet_title}")
    
    # Get the spreadsheet values
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=report_id,
        range=f"{sheet_title}"
    ).execute()
    
    values = result.get('values', [])
    if not values:
        logger.error("No data found in report.")
        sys.exit(1)
    
    # Convert to DataFrame for easier analysis
    headers = values[0]
    data = values[1:] if len(values) > 1 else []
    df = pd.DataFrame(data, columns=headers)
    
    # Create a temporary directory
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Find sessions with missing metadata
    missing_metadata_count = 0
    updated_rows = []
    
    for i, row in df.iterrows():
        # Check if this row needs updating
        needs_update = False
        
        # Check for missing metadata fields
        if (pd.isna(row.get("Host Name")) or row.get("Host Name") == "Unknown" or
            pd.isna(row.get("Host Email")) or row.get("Host Email") == "Unknown" or
            pd.isna(row.get("Start Time")) or row.get("Start Time") == "" or
            pd.isna(row.get("Duration (minutes)")) or row.get("Duration (minutes)") == ""):
            needs_update = True
        
        if not needs_update:
            continue
        
        missing_metadata_count += 1
        logger.info(f"Row {i+1}: {row.get('Meeting Topic')} - Missing metadata")
        
        # Try to get meeting details from Zoom API
        meeting_id = row.get("Meeting ID")
        meeting_uuid = row.get("Meeting UUID")
        
        if meeting_id:
            # Try to get meeting details using meeting ID
            meeting_details = zoom_client.get_meeting_details(meeting_id)
            
            if meeting_details:
                logger.info(f"Found meeting details for meeting ID: {meeting_id}")
                
                # Update row with meeting details
                row_dict = row.to_dict()
                
                if "host_id" in meeting_details:
                    host_id = meeting_details["host_id"]
                    user_details = zoom_client.get_user(host_id)
                    
                    if user_details:
                        row_dict["Host Name"] = f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}"
                        row_dict["Host Email"] = user_details.get("email", row_dict.get("Host Email", "Unknown"))
                
                if "start_time" in meeting_details:
                    row_dict["Start Time"] = meeting_details["start_time"]
                
                if "duration" in meeting_details:
                    row_dict["Duration (minutes)"] = meeting_details["duration"]
                
                updated_rows.append((i+1, row_dict))
                continue
        
        if meeting_uuid:
            # Try to get recording details using meeting UUID
            recording_details = zoom_client.get_recording_details(meeting_uuid)
            
            if recording_details:
                logger.info(f"Found recording details for meeting UUID: {meeting_uuid}")
                
                # Update row with recording details
                row_dict = row.to_dict()
                
                if "host_id" in recording_details:
                    host_id = recording_details["host_id"]
                    user_details = zoom_client.get_user(host_id)
                    
                    if user_details:
                        row_dict["Host Name"] = f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}"
                        row_dict["Host Email"] = user_details.get("email", row_dict.get("Host Email", "Unknown"))
                
                if "start_time" in recording_details:
                    row_dict["Start Time"] = recording_details["start_time"]
                
                if "duration" in recording_details:
                    row_dict["Duration (minutes)"] = recording_details["duration"]
                
                # Check for transcript URL
                if "recording_files" in recording_details:
                    for file in recording_details["recording_files"]:
                        if file.get("file_type") == "TRANSCRIPT":
                            row_dict["Transcript URL"] = file.get("download_url", "")
                        elif file.get("file_type") == "MP4":
                            row_dict["Zoom Video URL"] = file.get("play_url", "")
                
                updated_rows.append((i+1, row_dict))
    
    logger.info(f"Found {missing_metadata_count} sessions with missing metadata")
    logger.info(f"Updated {len(updated_rows)} sessions with metadata from Zoom API")
    
    # Update the spreadsheet with the new metadata
    if updated_rows:
        # Prepare batch update
        batch_update_values = []
        
        for row_index, row_dict in updated_rows:
            # Convert row_dict to list in the same order as headers
            row_values = [row_dict.get(header, "") for header in headers]
            
            batch_update_values.append({
                "range": f"{sheet_title}!A{row_index+1}:{chr(65+len(headers)-1)}{row_index+1}",
                "values": [row_values]
            })
        
        # Execute batch update
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": batch_update_values
        }
        
        result = sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=report_id,
            body=body
        ).execute()
        
        logger.info(f"Updated {result.get('totalUpdatedCells')} cells in the report")
    
    logger.info("Metadata update completed")

async def main():
    """Main function."""
    await update_session_metadata()

if __name__ == "__main__":
    asyncio.run(main()) 