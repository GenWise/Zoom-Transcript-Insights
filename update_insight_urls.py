#!/usr/bin/env python3
"""
Script to update the Zoom Report with insight URLs by matching meeting UUIDs.
This script will:
1. Connect to Google Drive
2. Find all session folders with generated insights
3. Extract meeting UUID from metadata or transcript
4. Match with the report by UUID
5. Update the report with insight URLs
"""

import os
import sys
import json
import logging
import asyncio
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from app.services.drive_manager import get_drive_service

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
    
    def download_file(self, file_id: str) -> Optional[str]:
        """
        Download a file from Drive and return its content.
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            File content as string, or None if failed
        """
        try:
            logger.debug(f"Downloading file with ID: {file_id}")
            
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

def extract_uuid_from_metadata(metadata_content: str) -> Optional[str]:
    """
    Extract meeting UUID from metadata JSON.
    
    Args:
        metadata_content: Content of metadata file
        
    Returns:
        Meeting UUID or None if not found
    """
    try:
        data = json.loads(metadata_content)
        return data.get("uuid")
    except Exception as e:
        logger.error(f"Error parsing metadata: {e}")
        return None

def extract_uuid_from_transcript(transcript_content: str) -> Optional[str]:
    """
    Extract meeting UUID from transcript file.
    
    Args:
        transcript_content: Content of transcript file
        
    Returns:
        Meeting UUID or None if not found
    """
    # Look for UUID pattern in transcript
    uuid_pattern = r'[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}'
    match = re.search(uuid_pattern, transcript_content)
    if match:
        return match.group(0)
    return None

async def update_report_with_insight_urls():
    """Update the Zoom Report with insight URLs for all sessions."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    logger.info(f"Updating Zoom Report with ID: {report_id}")
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Get the report data
    sheet_metadata = drive_manager.sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        return
        
    # Use the first sheet's title
    sheet_title = sheets[0]['properties']['title']
    logger.info(f"Using sheet: {sheet_title}")
    
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
    
    # Create a mapping of meeting topics to row indices
    topic_to_row = {}
    uuid_to_row = {}
    
    for i, row in enumerate(values):
        if i == 0:  # Skip header row
            continue
        
        if len(row) > topic_col_idx and row[topic_col_idx]:
            topic = row[topic_col_idx]
            topic_to_row[topic] = i
        
        if uuid_col_idx != -1 and len(row) > uuid_col_idx and row[uuid_col_idx]:
            uuid = row[uuid_col_idx]
            uuid_to_row[uuid] = i
    
    logger.info(f"Found {len(topic_to_row)} meeting topics and {len(uuid_to_row)} UUIDs in the report")
    
    # Process all course folders
    total_sessions = 0
    updated_sessions = 0
    
    for course_folder in course_folders:
        course_name = course_folder["name"]
        logger.info(f"Processing course: {course_name}")
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            total_sessions += 1
            
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
            
            metadata_file = None
            transcript_file = None
            
            for file in files:
                file_name = file["name"]
                
                if file_name in insight_files:
                    insight_files[file_name] = file
                elif file_name == "meeting_metadata.json":
                    metadata_file = file
                elif file_name.endswith(".vtt") or file_name == "transcript.vtt":
                    transcript_file = file
            
            # Check if any insight files exist
            has_insights = any(file for file in insight_files.values())
            if not has_insights:
                logger.debug(f"No insight files found for session: {session_name}")
                continue
            
            # Try to find matching row in the report
            row_idx = None
            
            # Try to find exact match by session name
            for topic, idx in topic_to_row.items():
                if session_name == topic:
                    row_idx = idx
                    logger.info(f"Found exact match for session: {session_name}")
                    break
            
            # If not found, try partial matching
            if row_idx is None:
                for topic, idx in topic_to_row.items():
                    # Extract date from session name (format: Course_YYYY-MM-DD)
                    session_date_match = re.search(r'_(\d{4}-\d{2}-\d{2})$', session_name)
                    if session_date_match:
                        session_date = session_date_match.group(1)
                        if session_date in topic:
                            row_idx = idx
                            logger.info(f"Found date match for session: {session_name} with date {session_date}")
                            break
                    
                    # Try if session name is contained in topic
                    if session_name in topic:
                        row_idx = idx
                        logger.info(f"Found partial match for session: {session_name}")
                        break
                    
                    # Try if topic is contained in session name
                    if topic in session_name:
                        row_idx = idx
                        logger.info(f"Found reverse partial match for session: {session_name}")
                        break
            
            # If still not found, try to get UUID from metadata and match
            if row_idx is None and metadata_file and uuid_to_row:
                metadata_content = drive_manager.download_file(metadata_file["id"])
                if metadata_content:
                    meeting_uuid = extract_uuid_from_metadata(metadata_content)
                    if meeting_uuid and meeting_uuid in uuid_to_row:
                        row_idx = uuid_to_row[meeting_uuid]
                        logger.info(f"Found UUID match for session: {session_name}")
            
            # If still not found, try to get UUID from transcript and match
            if row_idx is None and transcript_file and uuid_to_row:
                transcript_content = drive_manager.download_file(transcript_file["id"])
                if transcript_content:
                    meeting_uuid = extract_uuid_from_transcript(transcript_content)
                    if meeting_uuid and meeting_uuid in uuid_to_row:
                        row_idx = uuid_to_row[meeting_uuid]
                        logger.info(f"Found UUID match from transcript for session: {session_name}")
            
            if row_idx is None:
                logger.warning(f"Could not find matching row for session: {session_name}")
                continue
            
            # Prepare updates
            updates = []
            
            # Map insight files to URL columns
            file_to_column = {
                "executive_summary.md": "Executive Summary URL",
                "pedagogical_analysis.md": "Pedagogical Analysis URL",
                "aha_moments.md": "Aha Moments URL",
                "engagement_metrics.json": "Engagement Metrics URL",
                "concise_summary.md": "Concise Summary URL"
            }
            
            for file_name, file in insight_files.items():
                if not file:
                    continue
                
                column_name = file_to_column.get(file_name)
                if not column_name or url_columns[column_name] == -1:
                    continue
                
                col_idx = url_columns[column_name]
                
                # Get the webViewLink
                file_detail = drive_manager.service.files().get(
                    fileId=file["id"],
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
                logger.debug(f"No updates to make for session: {session_name}")
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
                
                updated_sessions += 1
                logger.info(f"Updated {len(updates)} cells for session: {session_name}")
            except Exception as e:
                logger.error(f"Error updating report for session {session_name}: {e}")
    
    logger.info(f"Processing completed. Updated {updated_sessions} out of {total_sessions} sessions.")

async def main():
    """Main function."""
    await update_report_with_insight_urls()

if __name__ == "__main__":
    asyncio.run(main()) 