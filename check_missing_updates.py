#!/usr/bin/env python3
"""
Script to check which sessions weren't updated in the Zoom report.
This will help identify sessions that need manual attention.
"""

import os
import sys
import json
import logging
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
        logger.debug(f"Listing folders with query: {query}")
        
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
            logger.debug(f"Retrieved {len(page_results)} folders in this page")
            
            page_token = response.get("nextPageToken")
            
            if not page_token:
                break
                
        logger.debug(f"Found total of {len(results)} folders")
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
        logger.debug(f"Listing files with query: {query}")
        
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
            logger.debug(f"Retrieved {len(page_results)} files in this page")
            
            page_token = response.get("nextPageToken")
            
            if not page_token:
                break
                
        logger.debug(f"Found total of {len(results)} files")
        return results

def check_missing_updates():
    """Check which sessions weren't updated in the Zoom report."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    logger.info(f"Checking missing updates for Zoom Report with ID: {report_id}")
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Track all sessions with insights
    all_sessions = []
    sessions_with_insights = []
    
    # Process all course folders
    for course_folder in course_folders:
        course_name = course_folder["name"]
        logger.info(f"Processing course: {course_name}")
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            all_sessions.append(session_name)
            
            # List files in the session folder
            files = drive_manager.list_files(session_folder["id"])
            
            # Check if insight files exist
            insight_files = {
                "executive_summary.md": None,
                "pedagogical_analysis.md": None,
                "aha_moments.md": None,
                "engagement_metrics.json": None,
                "concise_summary.md": None
            }
            
            for file in files:
                file_name = file["name"]
                if file_name in insight_files:
                    insight_files[file_name] = file
            
            # Check if any insight files exist
            has_insights = any(file for file in insight_files.values())
            if has_insights:
                sessions_with_insights.append(session_name)
    
    logger.info(f"Total sessions: {len(all_sessions)}")
    logger.info(f"Sessions with insights: {len(sessions_with_insights)}")
    
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
    
    if topic_col_idx == -1:
        logger.error("Meeting Topic column not found in report.")
        return
    
    # Map column names to indices
    url_columns = {
        "Executive Summary URL": -1,
        "Pedagogical Analysis URL": -1,
        "Aha Moments URL": -1,
        "Engagement Metrics URL": -1,
        "Concise Summary URL": -1
    }
    
    for header, _ in url_columns.items():
        try:
            url_columns[header] = headers.index(header)
        except ValueError:
            logger.warning(f"Column '{header}' not found in report.")
    
    # Check which sessions in the report have been updated
    updated_sessions = set()
    
    for i, row in enumerate(values):
        if i == 0:  # Skip header row
            continue
            
        if len(row) <= topic_col_idx:
            continue
            
        topic = row[topic_col_idx]
        
        # Check if any URL column has a value
        has_url = False
        for col_name, col_idx in url_columns.items():
            if col_idx != -1 and len(row) > col_idx and row[col_idx]:
                has_url = True
                break
                
        if has_url:
            updated_sessions.add(topic)
    
    logger.info(f"Sessions in report with URLs: {len(updated_sessions)}")
    
    # Find sessions with insights that weren't updated
    missing_updates = []
    for session in sessions_with_insights:
        found = False
        for topic in updated_sessions:
            if session == topic or session in topic or topic in session:
                found = True
                break
                
        if not found:
            missing_updates.append(session)
    
    logger.info(f"Sessions with insights but no URLs in report: {len(missing_updates)}")
    
    # Print the missing sessions
    if missing_updates:
        logger.info("Sessions that need manual attention:")
        for session in missing_updates:
            logger.info(f"  - {session}")

if __name__ == "__main__":
    check_missing_updates() 