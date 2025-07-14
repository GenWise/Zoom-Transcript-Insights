#!/usr/bin/env python3
"""
Script to populate the Zoom Report with all existing sessions from Google Drive.

This script will:
1. Scan all course folders in Google Drive
2. Find all session folders with generated insights
3. Create entries for each session in the Zoom Report
4. Update the report with insight URLs

This is a one-time script to ensure all sessions are in the report.
"""

import os
import sys
import json
import logging
import asyncio
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

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

def extract_date_from_folder_name(folder_name: str) -> Optional[str]:
    """
    Extract date from folder name (format: Course_YYYY-MM-DD).
    
    Args:
        folder_name: Name of the folder
        
    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    date_match = re.search(r'_(\d{4}-\d{2}-\d{2})$', folder_name)
    if date_match:
        return date_match.group(1)
    return None

async def populate_report():
    """Populate the Zoom Report with all existing sessions from Google Drive."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    logger.info(f"Populating Zoom Report with ID: {report_id}")
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Try to download existing report data
    existing_report_data = []
    existing_report_downloaded = False
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        logger.info(f"Downloading existing report with ID: {report_id}")
        
        # Export the Google Sheet as CSV
        request = drive_manager.service.files().export_media(
            fileId=report_id,
            mimeType='text/csv'
        )
        
        existing_report_path = os.path.join(temp_dir, "existing_zoom_report.csv")
        
        with open(existing_report_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
        
        # Read the existing report
        if os.path.exists(existing_report_path) and os.path.getsize(existing_report_path) > 0:
            existing_df = pd.read_csv(existing_report_path)
            existing_report_data = existing_df.to_dict('records')
            existing_headers = list(existing_df.columns)
            logger.info(f"Successfully downloaded existing report with {len(existing_report_data)} entries")
            existing_report_downloaded = True
    except Exception as e:
        logger.warning(f"Could not download existing report: {e}")
        existing_headers = [
            "Meeting Topic", "Host Name", "Host Email", "Date", "Start Time", 
            "Duration (minutes)", "Has Transcript", "Transcript URL", "Meeting UUID", 
            "Meeting ID", "Size (MB)", "Zoom Video URL", "Executive Summary URL", 
            "Pedagogical Analysis URL", "Aha Moments URL", "Engagement Metrics URL", 
            "Concise Summary URL"
        ]
    
    # Collect all session data
    all_sessions = []
    total_sessions = 0
    
    for course_folder in course_folders:
        course_name = course_folder["name"]
        logger.info(f"Processing course: {course_name}")
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            total_sessions += 1
            
            # Extract date from session folder name
            session_date = extract_date_from_folder_name(session_name)
            if not session_date:
                logger.warning(f"Could not extract date from session folder name: {session_name}")
                session_date = "Unknown"
            
            # Format date for display (YYYY-MM-DD to dd mmm yyyy)
            try:
                display_date = datetime.strptime(session_date, "%Y-%m-%d").strftime("%d %b %Y")
            except ValueError:
                display_date = session_date
            
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
            meeting_uuid = ""
            
            for file in files:
                file_name = file["name"]
                
                if file_name in insight_files:
                    insight_files[file_name] = file
                elif file_name == "meeting_metadata.json":
                    metadata_file = file
                elif file_name.endswith(".vtt") or file_name == "transcript.vtt":
                    transcript_file = file
            
            # Extract UUID from metadata if available
            if metadata_file:
                metadata_content = drive_manager.download_file(metadata_file["id"])
                if metadata_content:
                    try:
                        metadata = json.loads(metadata_content)
                        meeting_uuid = metadata.get("meeting_uuid", "")
                    except Exception as e:
                        logger.error(f"Error parsing metadata for session {session_name}: {e}")
            
            # Prepare insight URLs
            insight_urls = {
                "Executive Summary URL": "",
                "Pedagogical Analysis URL": "",
                "Aha Moments URL": "",
                "Engagement Metrics URL": "",
                "Concise Summary URL": ""
            }
            
            # Get insight URLs
            file_mapping = {
                "executive_summary.md": "Executive Summary URL",
                "pedagogical_analysis.md": "Pedagogical Analysis URL",
                "aha_moments.md": "Aha Moments URL",
                "engagement_metrics.json": "Engagement Metrics URL",
                "concise_summary.md": "Concise Summary URL"
            }
            
            # Get insight URLs
            for file_name, file in insight_files.items():
                if not file:
                    continue
                
                column_name = file_mapping.get(file_name)
                if not column_name:
                    continue
                
                # Get the webViewLink
                file_detail = drive_manager.service.files().get(
                    fileId=file["id"],
                    fields="webViewLink",
                    supportsAllDrives=True
                ).execute()
                
                insight_urls[column_name] = file_detail.get("webViewLink", "")
            
            # Create session data
            session_data = {
                "Meeting Topic": session_name.split("_")[0],  # Remove date suffix
                "Host Name": "Unknown",  # We don't have host info without metadata
                "Host Email": "Unknown",
                "Date": display_date,
                "Start Time": "",
                "Duration (minutes)": "",
                "Has Transcript": "TRUE" if transcript_file else "FALSE",
                "Transcript URL": "",
                "Meeting UUID": meeting_uuid,
                "Meeting ID": "",
                "Size (MB)": "",
                "Zoom Video URL": "",
                "Executive Summary URL": insight_urls["Executive Summary URL"],
                "Pedagogical Analysis URL": insight_urls["Pedagogical Analysis URL"],
                "Aha Moments URL": insight_urls["Aha Moments URL"],
                "Engagement Metrics URL": insight_urls["Engagement Metrics URL"],
                "Concise Summary URL": insight_urls["Concise Summary URL"]
            }
            
            # Add session data to list
            all_sessions.append(session_data)
            
            logger.info(f"Processed session: {session_name}")
    
    logger.info(f"Found {len(all_sessions)} sessions in Google Drive")
    
    # Merge with existing report data
    merged_report_data = []
    
    if existing_report_downloaded and existing_report_data:
        # Create a set of UUIDs and session names from existing report
        existing_uuids = {record.get("Meeting UUID") for record in existing_report_data if record.get("Meeting UUID")}
        existing_names_dates = {(record.get("Meeting Topic"), record.get("Date")) for record in existing_report_data}
        
        # Add all existing records
        merged_report_data.extend(existing_report_data)
        
        # Add new sessions that don't exist in the report
        new_sessions_added = 0
        for session in all_sessions:
            # Check if session already exists by UUID or name+date
            if (session.get("Meeting UUID") and session.get("Meeting UUID") in existing_uuids) or \
               ((session.get("Meeting Topic"), session.get("Date")) in existing_names_dates):
                continue
            
            # Add new session
            merged_report_data.append(session)
            new_sessions_added += 1
        
        logger.info(f"Added {new_sessions_added} new sessions to the report")
    else:
        # If no existing data, just use all sessions
        merged_report_data = all_sessions
        logger.info(f"Creating new report with {len(all_sessions)} sessions")
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(merged_report_data)
    
    # Ensure all columns are present in the correct order
    for column in existing_headers:
        if column not in df.columns:
            df[column] = ""
    
    df = df[existing_headers]
    
    # Ensure URLs don't spill over by setting display.max_colwidth
    with pd.option_context('display.max_colwidth', None):
        report_path = os.path.join(temp_dir, "populated_zoom_report.csv")
        df.to_csv(report_path, index=False)
    logger.info(f"Saved merged report to {report_path}")
    
    # Upload to Google Drive
    try:
        # Create media
        media = MediaFileUpload(
            report_path,
            mimetype='text/csv',
            resumable=True
        )
        
        # Update file content
        logger.info(f"Updating report with ID: {report_id}")
        
        # Update the file
        file = drive_manager.service.files().update(
            fileId=report_id,
            media_body=media,
            supportsAllDrives=True
        ).execute()
        
        # Get the webViewLink
        file = drive_manager.service.files().get(
            fileId=report_id,
            fields='webViewLink',
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Report updated successfully")
        logger.info(f"Report can be viewed at: {file.get('webViewLink')}")
    except Exception as e:
        logger.error(f"Error uploading report to Google Drive: {e}")
        logger.info(f"Report is still available locally at: {report_path}")

async def main():
    """Main function."""
    await populate_report()

if __name__ == "__main__":
    asyncio.run(main()) 