#!/usr/bin/env python3
"""
Script to verify that all sessions with insights have URLs in the Zoom report.
This will provide a summary of the update process.
"""

import os
import sys
import logging
from typing import Dict, List, Set
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

def get_sessions_with_insights() -> Dict[str, Dict[str, List[str]]]:
    """
    Get all sessions with insights.
    
    Returns:
        Dictionary mapping course names to session names and their insight types
    """
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    logger.info(f"Found {len(course_folders)} course folders")
    
    # Track all sessions with insights
    sessions_with_insights = {}
    
    # Process all course folders
    for course_folder in course_folders:
        course_name = course_folder["name"]
        logger.info(f"Processing course: {course_name}")
        
        sessions_with_insights[course_name] = {}
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            
            # List files in the session folder
            files = drive_manager.list_files(session_folder["id"])
            
            # Check which insight files exist
            insight_files = []
            
            for file in files:
                file_name = file["name"]
                if file_name in ["executive_summary.md", "pedagogical_analysis.md", 
                                "aha_moments.md", "engagement_metrics.json", 
                                "concise_summary.md"]:
                    insight_files.append(file_name)
            
            # Add to the dictionary if any insight files exist
            if insight_files:
                sessions_with_insights[course_name][session_name] = insight_files
    
    return sessions_with_insights

def get_report_sessions_with_urls() -> Dict[str, Set[str]]:
    """
    Get all sessions in the report that have URLs.
    
    Returns:
        Dictionary mapping session names to sets of URL column names
    """
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return {}
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Get the report data
    sheet_metadata = drive_manager.sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        return {}
        
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
        return {}
        
    headers = values[0]
    
    # Find relevant column indices
    topic_col_idx = -1
    
    for i, header in enumerate(headers):
        if "Meeting Topic" in header:
            topic_col_idx = i
            break
    
    if topic_col_idx == -1:
        logger.error("Meeting Topic column not found in report.")
        return {}
    
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
    
    # Check which sessions in the report have URLs
    sessions_with_urls = {}
    
    for i, row in enumerate(values):
        if i == 0:  # Skip header row
            continue
            
        if len(row) <= topic_col_idx:
            continue
            
        topic = row[topic_col_idx]
        if not topic:
            continue
        
        # Check which URL columns have values
        urls_present = set()
        for col_name, col_idx in url_columns.items():
            if col_idx != -1 and len(row) > col_idx and row[col_idx]:
                urls_present.add(col_name)
                
        if urls_present:
            sessions_with_urls[topic] = urls_present
    
    return sessions_with_urls

def verify_report_updates():
    """Verify that all sessions with insights have URLs in the Zoom report."""
    # Get sessions with insights
    sessions_with_insights = get_sessions_with_insights()
    
    # Get sessions in the report with URLs
    report_sessions_with_urls = get_report_sessions_with_urls()
    
    # Count total sessions with insights
    total_sessions_with_insights = 0
    total_insight_files = 0
    
    for course_name, sessions in sessions_with_insights.items():
        total_sessions_with_insights += len(sessions)
        for session_name, insight_files in sessions.items():
            total_insight_files += len(insight_files)
    
    logger.info(f"Total sessions with insights: {total_sessions_with_insights}")
    logger.info(f"Total insight files: {total_insight_files}")
    logger.info(f"Sessions in report with URLs: {len(report_sessions_with_urls)}")
    
    # Check if all sessions with insights have URLs in the report
    matched_sessions = 0
    unmatched_sessions = []
    
    for course_name, sessions in sessions_with_insights.items():
        for session_name, insight_files in sessions.items():
            found = False
            for report_session in report_sessions_with_urls:
                if session_name == report_session or session_name in report_session or report_session in session_name:
                    matched_sessions += 1
                    found = True
                    break
            
            if not found:
                unmatched_sessions.append((course_name, session_name))
    
    logger.info(f"Sessions with insights matched to report: {matched_sessions}")
    
    if unmatched_sessions:
        logger.warning(f"Found {len(unmatched_sessions)} sessions with insights but no URLs in report:")
        for course_name, session_name in unmatched_sessions:
            logger.warning(f"  - {course_name}: {session_name}")
    else:
        logger.info("All sessions with insights have URLs in the report!")
    
    # Check if all URL types are present for each session
    sessions_with_missing_urls = []
    
    for course_name, sessions in sessions_with_insights.items():
        for session_name, insight_files in sessions.items():
            for report_session, urls_present in report_sessions_with_urls.items():
                if session_name == report_session or session_name in report_session or report_session in session_name:
                    # Map insight files to URL column names
                    expected_urls = set()
                    if "executive_summary.md" in insight_files:
                        expected_urls.add("Executive Summary URL")
                    if "pedagogical_analysis.md" in insight_files:
                        expected_urls.add("Pedagogical Analysis URL")
                    if "aha_moments.md" in insight_files:
                        expected_urls.add("Aha Moments URL")
                    if "engagement_metrics.json" in insight_files:
                        expected_urls.add("Engagement Metrics URL")
                    if "concise_summary.md" in insight_files:
                        expected_urls.add("Concise Summary URL")
                    
                    missing_urls = expected_urls - urls_present
                    if missing_urls:
                        sessions_with_missing_urls.append((course_name, session_name, list(missing_urls)))
    
    if sessions_with_missing_urls:
        logger.warning(f"Found {len(sessions_with_missing_urls)} sessions with missing URL types:")
        for course_name, session_name, missing_urls in sessions_with_missing_urls:
            logger.warning(f"  - {course_name}: {session_name} - Missing: {', '.join(missing_urls)}")
    else:
        logger.info("All sessions have all expected URL types in the report!")

if __name__ == "__main__":
    verify_report_updates() 