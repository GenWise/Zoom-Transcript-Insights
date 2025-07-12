#!/usr/bin/env python3
"""
Script to check if sessions with specific UUIDs have insight files in Google Drive.
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

# List of UUIDs to check
UUIDS_TO_CHECK = [
    "3WBiM2lVRUGt0+OygwVDwg==",
    "siCBRGssT2+dOR5SB8NTlQ==",
    "dLDARJPASAm5q7zZiFKpeQ==",
    "OAJBcGh+SYyvMIEH8XzHRA==",
    "lx3zo2j9QJGAnFSyuEbvzg==",
    "vPCj27EqRdCln9DuWXfKFA==",
    "klV4xrb9RIenHLJ6KzVaOw==",
    "/Gbq3fsCR4y3sttCe0QSKQ==",
    "+gXZekI8SVaoBllZFbZxmQ==",
    "BWeFsBZOR6GsN2DVqjKUFA=="
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
    
    def download_file(self, file_id: str) -> Optional[str]:
        """
        Download a file from Drive and return its content.
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            File content as string, or None if failed
        """
        try:
            if self.use_shared_drive:
                request = self.service.files().get_media(
                    fileId=file_id,
                    supportsAllDrives=True
                )
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            content = request.execute()
            
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='replace')
            return content
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

def extract_uuid_from_metadata(content: str) -> Optional[str]:
    """
    Extract UUID from metadata JSON content.
    
    Args:
        content: Content of the metadata file
        
    Returns:
        UUID if found, None otherwise
    """
    try:
        data = json.loads(content)
        return data.get("uuid")
    except Exception as e:
        logger.error(f"Error parsing metadata: {e}")
        return None

def extract_uuid_from_transcript(content: str) -> Optional[str]:
    """
    Extract UUID from transcript content.
    
    Args:
        content: Content of the transcript file
        
    Returns:
        UUID if found, None otherwise
    """
    # Look for UUID pattern in transcript
    uuid_pattern = r'[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}'
    match = re.search(uuid_pattern, content)
    if match:
        return match.group(0)
    
    # Look for base64 encoded UUID pattern
    uuid_pattern = r'[a-zA-Z0-9+/]{22}=='
    match = re.search(uuid_pattern, content)
    if match:
        return match.group(0)
    
    return None

def get_report_data() -> Tuple[Dict[str, str], Dict[str, List[int]]]:
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

def check_uuid_insights():
    """Check if sessions with specific UUIDs have insight files in Google Drive."""
    # Get report data
    uuid_to_topic, uuid_to_row = get_report_data()
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Track sessions with UUIDs
    sessions_with_uuids = {}
    
    # Process all course folders
    for course_folder in course_folders:
        course_name = course_folder["name"]
        logger.debug(f"Processing course: {course_name}")
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            
            # List files in the session folder
            files = drive_manager.list_files(session_folder["id"])
            
            # Check for metadata or transcript files
            metadata_file = None
            transcript_file = None
            
            for file in files:
                if file["name"] == "meeting_metadata.json":
                    metadata_file = file
                elif file["name"].endswith(".vtt") or file["name"] == "transcript.vtt":
                    transcript_file = file
            
            # Extract UUID from metadata or transcript
            session_uuid = None
            
            if metadata_file:
                content = drive_manager.download_file(metadata_file["id"])
                if content:
                    session_uuid = extract_uuid_from_metadata(content)
            
            if not session_uuid and transcript_file:
                content = drive_manager.download_file(transcript_file["id"])
                if content:
                    session_uuid = extract_uuid_from_transcript(content)
            
            # If UUID is in our list to check
            if session_uuid in UUIDS_TO_CHECK:
                # Check for insight files
                insight_files = []
                
                for file in files:
                    if file["name"] in ["executive_summary.md", "pedagogical_analysis.md", 
                                      "aha_moments.md", "engagement_metrics.json", 
                                      "concise_summary.md"]:
                        insight_files.append(file["name"])
                
                sessions_with_uuids[session_uuid] = {
                    "course": course_name,
                    "session": session_name,
                    "folder_id": session_folder["id"],
                    "insight_files": insight_files
                }
    
    # Check each UUID
    for uuid in UUIDS_TO_CHECK:
        topic = uuid_to_topic.get(uuid, "Unknown")
        
        if uuid in sessions_with_uuids:
            session_info = sessions_with_uuids[uuid]
            logger.info(f"UUID {uuid} found in Drive (Topic in report: {topic})")
            logger.info(f"  - Course: {session_info['course']}")
            logger.info(f"  - Session: {session_info['session']}")
            
            if session_info["insight_files"]:
                logger.info(f"  - Has {len(session_info['insight_files'])} insight files:")
                for file in session_info["insight_files"]:
                    logger.info(f"    - {file}")
            else:
                logger.warning(f"  - No insight files found")
        else:
            logger.warning(f"UUID {uuid} (Topic: {topic}) NOT found in Drive")
    
    # Count UUIDs with insights
    uuids_with_insights = sum(1 for uuid in UUIDS_TO_CHECK if uuid in sessions_with_uuids and sessions_with_uuids[uuid]["insight_files"])
    
    logger.info(f"Summary: Found {len(sessions_with_uuids)}/{len(UUIDS_TO_CHECK)} UUIDs in Drive")
    logger.info(f"         {uuids_with_insights}/{len(sessions_with_uuids)} UUIDs have insight files")

if __name__ == "__main__":
    check_uuid_insights() 