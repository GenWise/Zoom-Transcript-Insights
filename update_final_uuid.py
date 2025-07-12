#!/usr/bin/env python3
"""
Script to update insight URLs for the final UUID in the Zoom report.
"""

import os
import sys
import json
import logging
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

# The UUID to update
UUID_TO_UPDATE = "aDZ1kD0ATmOGOUdlbBN4mA=="

class DriveManager:
    """Class for interacting with Google Drive."""
    
    def __init__(self):
        """Initialize the Drive manager."""
        credentials_file = config.GOOGLE_CREDENTIALS_FILE
        scopes = ["https://www.googleapis.com/auth/drive"]
        
        logger.info(f"Initializing Drive Manager")
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        
        self.service = build("drive", "v3", credentials=credentials)
        self.sheets_service = build("sheets", "v4", credentials=credentials)
        self.root_folder_id = config.GOOGLE_DRIVE_ROOT_FOLDER
        self.use_shared_drive = config.USE_SHARED_DRIVE
        self.shared_drive_id = config.GOOGLE_SHARED_DRIVE_ID if config.USE_SHARED_DRIVE else None
        
        if self.use_shared_drive:
            logger.info(f"Drive Manager initialized with shared drive ID: {self.shared_drive_id}")
        else:
            logger.info(f"Drive Manager initialized with root folder ID: {self.root_folder_id}")
    
    def list_folders(self, parent_id: str) -> List[Dict]:
        """
        List all folders in a parent folder.
        
        Args:
            parent_id: ID of the parent folder
            
        Returns:
            List of folder objects
        """
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = []
        page_token = None
        
        while True:
            if self.use_shared_drive:
                response = self.service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                    corpora="drive",
                    driveId=self.shared_drive_id,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()
            else:
                response = self.service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token
                ).execute()
            
            page_results = response.get("files", [])
            results.extend(page_results)
            
            page_token = response.get("nextPageToken")
            
            if not page_token:
                break
                
        return results
    
    def list_files(self, parent_id: str) -> List[Dict]:
        """
        List all files in a folder.
        
        Args:
            parent_id: ID of the parent folder
            
        Returns:
            List of file objects
        """
        query = f"'{parent_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
        
        results = []
        page_token = None
        
        while True:
            if self.use_shared_drive:
                response = self.service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, webViewLink)",
                    pageToken=page_token,
                    corpora="drive",
                    driveId=self.shared_drive_id,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()
            else:
                response = self.service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, webViewLink)",
                    pageToken=page_token
                ).execute()
            
            page_results = response.get("files", [])
            results.extend(page_results)
            
            page_token = response.get("nextPageToken")
            
            if not page_token:
                break
                
        return results

def update_final_uuid():
    """Update insight URLs for the final UUID in the Zoom report."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get the report data
    sheet_metadata = drive_manager.sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        return
        
    # Use the first sheet's title
    sheet_title = sheets[0]['properties']['title']
    
    # Get the spreadsheet values
    result = drive_manager.sheets_service.spreadsheets().values().get(
        spreadsheetId=report_id,
        range=f"{sheet_title}!A1:Q1000"
    ).execute()
        
    values = result.get('values', [])
    if not values:
        logger.error("No data found in report.")
        return
        
    headers = values[0]
    
    # Find relevant column indices
    topic_col_idx = -1
    uuid_col_idx = -1
    
    for i, header in enumerate(headers):
        if "Meeting Topic" in header:
            topic_col_idx = i
        elif "UUID" in header:
            uuid_col_idx = i
    
    if uuid_col_idx == -1 or topic_col_idx == -1:
        logger.error("Required columns not found in report.")
        return
    
    # Find the row for the UUID
    row_idx = -1
    topic = ""
    
    for i, row in enumerate(values):
        if i == 0:  # Skip header row
            continue
            
        if len(row) <= uuid_col_idx:
            continue
            
        if row[uuid_col_idx] == UUID_TO_UPDATE:
            row_idx = i
            topic = row[topic_col_idx] if len(row) > topic_col_idx else ""
            break
    
    if row_idx == -1:
        logger.error(f"UUID {UUID_TO_UPDATE} not found in report.")
        return
    
    logger.info(f"Found UUID {UUID_TO_UPDATE} in report (Topic: {topic}, Row: {row_idx + 1})")
    
    # Map column names to indices
    url_columns = {
        "executive_summary.md": {"name": "Executive Summary URL", "index": -1},
        "pedagogical_analysis.md": {"name": "Pedagogical Analysis URL", "index": -1},
        "aha_moments.md": {"name": "Aha Moments URL", "index": -1},
        "engagement_metrics.json": {"name": "Engagement Metrics URL", "index": -1},
        "concise_summary.md": {"name": "Concise Summary URL", "index": -1}
    }
    
    for file_name, column_info in url_columns.items():
        try:
            column_info["index"] = headers.index(column_info["name"])
        except ValueError:
            logger.warning(f"Column '{column_info['name']}' not found in report.")
    
    # Find session folder by topic
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Search for matching session in all course folders
    session_folder_id = None
    session_name = ""
    course_name = ""
    
    for course_folder in course_folders:
        course_name_temp = course_folder["name"]
        
        # Check if course name is in the topic
        if course_name_temp in topic:
            logger.info(f"Found potential course match: {course_name_temp}")
            
            # Get all session folders
            session_folders = drive_manager.list_folders(course_folder["id"])
            
            for session_folder in session_folders:
                session_name_temp = session_folder["name"]
                
                # List files to look for metadata or transcript with UUID
                files = drive_manager.list_files(session_folder["id"])
                
                # Check for insight files first
                insight_files = []
                for file in files:
                    if file["name"] in ["executive_summary.md", "pedagogical_analysis.md", 
                                      "aha_moments.md", "engagement_metrics.json", 
                                      "concise_summary.md"]:
                        insight_files.append(file["name"])
                
                if insight_files:
                    # This session has insights, check if it matches by name
                    if (topic in session_name_temp or 
                        session_name_temp in topic or 
                        any(word in session_name_temp for word in topic.split())):
                        session_folder_id = session_folder["id"]
                        session_name = session_name_temp
                        course_name = course_name_temp
                        logger.info(f"Found matching session: {course_name}/{session_name}")
                        break
            
            if session_folder_id:
                break
    
    if not session_folder_id:
        logger.error(f"No matching session folder found for topic: {topic}")
        return
    
    # Find insight files
    files = drive_manager.list_files(session_folder_id)
    insight_files = {}
    
    for file in files:
        if file["name"] in ["executive_summary.md", "pedagogical_analysis.md", 
                          "aha_moments.md", "engagement_metrics.json", 
                          "concise_summary.md"]:
            insight_files[file["name"]] = file
    
    if not insight_files:
        logger.error("No insight files found in session folder.")
        return
    
    logger.info(f"Found {len(insight_files)} insight files:")
    for file_name in insight_files:
        logger.info(f"  - {file_name}")
    
    # Prepare updates
    updates = []
    
    for file_name, file_info in insight_files.items():
        column_info = url_columns.get(file_name)
        if not column_info or column_info["index"] == -1:
            continue
            
        col_idx = column_info["index"]
        
        # Get the webViewLink
        file_detail = drive_manager.service.files().get(
            fileId=file_info["id"],
            fields="webViewLink",
            supportsAllDrives=True
        ).execute()
        
        web_view_link = file_detail.get("webViewLink", "")
        
        # Convert to A1 notation
        col_letter = chr(ord('A') + col_idx)
        cell_range = f"{sheet_title}!{col_letter}{row_idx + 1}"
        
        # Print the current value
        current_value = values[row_idx][col_idx] if len(values[row_idx]) > col_idx else ""
        logger.info(f"Current value in cell {cell_range}: '{current_value}'")
        logger.info(f"New value: '{web_view_link}'")
        
        updates.append({
            "range": cell_range,
            "values": [[web_view_link]]
        })
    
    if not updates:
        logger.error("No updates to make.")
        return
        
    # Apply updates
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates
    }
    
    try:
        result = drive_manager.sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=report_id,
            body=body
        ).execute()
        
        logger.info(f"Updated {len(updates)} URLs for UUID {UUID_TO_UPDATE}")
    except Exception as e:
        logger.error(f"Error updating report: {e}")

if __name__ == "__main__":
    update_final_uuid() 