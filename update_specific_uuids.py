#!/usr/bin/env python3
"""
Script to update insight URLs for specific UUIDs in the Zoom report.
This script will find the sessions in Google Drive by topic name and update the URLs.
"""

import os
import sys
import json
import logging
import re
from typing import Dict, List, Set, Optional, Tuple
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

# List of UUIDs to update
UUIDS_TO_UPDATE = [
    "3WBiM2lVRUGt0+OygwVDwg==",  # Gifted Summer Program: Orientation
    "siCBRGssT2+dOR5SB8NTlQ==",  # Astrophysics
    "dLDARJPASAm5q7zZiFKpeQ==",  # Astrophysics
    "OAJBcGh+SYyvMIEH8XzHRA==",  # GenAI for Educators: Sri Kumarans
    "lx3zo2j9QJGAnFSyuEbvzg==",  # GenAI for Educators: Sri Kumarans
    "vPCj27EqRdCln9DuWXfKFA==",  # Astrophysics
    "klV4xrb9RIenHLJ6KzVaOw==",  # Algebranauts
    "/Gbq3fsCR4y3sttCe0QSKQ==",  # Beyond the Piggy Bank
    "+gXZekI8SVaoBllZFbZxmQ==",  # Algebranauts
    # "BWeFsBZOR6GsN2DVqjKUFA=="  # Beyond the Piggy Bank (already has URLs)
]

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

def get_report_data() -> Tuple[Dict[str, str], Dict[str, int]]:
    """
    Get data from the Zoom report.
    
    Returns:
        Tuple of (uuid_to_topic, uuid_to_row_idx) dictionaries
    """
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return {}, {}
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get the report data
    sheet_metadata = drive_manager.sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        return {}, {}
        
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
        return {}, {}
        
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
        return {}, {}
    
    # Map UUIDs to topics and row indices
    uuid_to_topic = {}
    uuid_to_row = {}
    
    for i, row in enumerate(values):
        if i == 0:  # Skip header row
            continue
            
        if len(row) <= uuid_col_idx:
            continue
            
        uuid = row[uuid_col_idx]
        if not uuid:
            continue
            
        topic = row[topic_col_idx] if len(row) > topic_col_idx else ""
        
        uuid_to_topic[uuid] = topic
        uuid_to_row[uuid] = i
    
    return uuid_to_topic, uuid_to_row

def find_session_folders_by_topic(drive_manager: DriveManager, topics: List[str]) -> Dict[str, Dict]:
    """
    Find session folders in Drive by topic name.
    
    Args:
        drive_manager: DriveManager instance
        topics: List of topic names to search for
        
    Returns:
        Dictionary mapping topic names to session folder info
    """
    topic_to_folder = {}
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Process all course folders
    for course_folder in course_folders:
        course_name = course_folder["name"]
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            
            # Check if this session matches any of the topics
            for topic in topics:
                # Try different matching strategies
                if (
                    topic == session_name or
                    topic in session_name or
                    session_name in topic or
                    course_name in topic
                ):
                    # Check if this session has insight files
                    files = drive_manager.list_files(session_folder["id"])
                    
                    insight_files = {}
                    for file in files:
                        if file["name"] in ["executive_summary.md", "pedagogical_analysis.md", 
                                          "aha_moments.md", "engagement_metrics.json", 
                                          "concise_summary.md"]:
                            insight_files[file["name"]] = file
                    
                    if insight_files:
                        topic_to_folder[topic] = {
                            "course": course_name,
                            "session": session_name,
                            "folder_id": session_folder["id"],
                            "insight_files": insight_files
                        }
                        logger.info(f"Found matching session for topic '{topic}': {course_name}/{session_name}")
                        break
    
    return topic_to_folder

def update_report_with_urls(drive_manager: DriveManager, uuid_to_topic: Dict[str, str], 
                           uuid_to_row: Dict[str, int], topic_to_folder: Dict[str, Dict]):
    """
    Update the Zoom report with insight URLs for specific UUIDs.
    
    Args:
        drive_manager: DriveManager instance
        uuid_to_topic: Dictionary mapping UUIDs to topic names
        uuid_to_row: Dictionary mapping UUIDs to row indices
        topic_to_folder: Dictionary mapping topic names to session folder info
    """
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
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
    
    # Update URLs for each UUID
    updated_uuids = 0
    
    for uuid in UUIDS_TO_UPDATE:
        if uuid not in uuid_to_topic or uuid not in uuid_to_row:
            logger.warning(f"UUID {uuid} not found in report")
            continue
            
        topic = uuid_to_topic[uuid]
        row_idx = uuid_to_row[uuid]
        
        if topic not in topic_to_folder:
            logger.warning(f"No matching session folder found for topic '{topic}' (UUID: {uuid})")
            continue
            
        session_info = topic_to_folder[topic]
        
        # Prepare updates
        updates = []
        
        for file_name, file_info in session_info["insight_files"].items():
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
            
            updates.append({
                "range": cell_range,
                "values": [[web_view_link]]
            })
        
        if not updates:
            logger.warning(f"No updates to make for UUID {uuid} (Topic: {topic})")
            continue
            
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
            
            updated_uuids += 1
            logger.info(f"Updated {len(updates)} URLs for UUID {uuid} (Topic: {topic})")
        except Exception as e:
            logger.error(f"Error updating report for UUID {uuid}: {e}")
    
    logger.info(f"Processing completed. Updated {updated_uuids} out of {len(UUIDS_TO_UPDATE)} UUIDs.")

def update_specific_uuids():
    """Update insight URLs for specific UUIDs in the Zoom report."""
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get report data
    uuid_to_topic, uuid_to_row = get_report_data()
    
    # Get topics for the UUIDs we want to update
    topics = [uuid_to_topic.get(uuid, "") for uuid in UUIDS_TO_UPDATE]
    topics = [topic for topic in topics if topic]  # Filter out empty topics
    
    if not topics:
        logger.error("No topics found for the specified UUIDs.")
        return
    
    logger.info(f"Found {len(topics)} topics for the specified UUIDs:")
    for uuid, topic in [(uuid, uuid_to_topic.get(uuid, "Unknown")) for uuid in UUIDS_TO_UPDATE]:
        logger.info(f"  - UUID {uuid}: {topic}")
    
    # Find session folders by topic
    topic_to_folder = find_session_folders_by_topic(drive_manager, topics)
    
    if not topic_to_folder:
        logger.error("No matching session folders found.")
        return
    
    logger.info(f"Found {len(topic_to_folder)} matching session folders.")
    
    # Update the report with URLs
    update_report_with_urls(drive_manager, uuid_to_topic, uuid_to_row, topic_to_folder)

if __name__ == "__main__":
    update_specific_uuids() 