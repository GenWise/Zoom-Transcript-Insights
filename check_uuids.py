#!/usr/bin/env python3
"""
Script to check if specific UUIDs exist in the Zoom report and if they have insight URLs.
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

def check_uuids_in_report():
    """Check if the specified UUIDs exist in the Zoom report and if they have insight URLs."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    logger.info(f"Checking UUIDs in Zoom Report with ID: {report_id}")
    
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
    
    if uuid_col_idx == -1:
        logger.error("UUID column not found in report.")
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
    
    # Check each UUID
    found_uuids = 0
    uuids_with_urls = 0
    
    for uuid in UUIDS_TO_CHECK:
        found = False
        has_urls = False
        row_idx = -1
        topic = ""
        
        for i, row in enumerate(values):
            if i == 0:  # Skip header row
                continue
                
            if len(row) <= uuid_col_idx:
                continue
                
            if row[uuid_col_idx] == uuid:
                found = True
                row_idx = i
                if len(row) > topic_col_idx:
                    topic = row[topic_col_idx]
                break
        
        if found:
            found_uuids += 1
            
            # Check if any URL columns have values
            url_count = 0
            missing_urls = []
            
            for col_name, col_idx in url_columns.items():
                if col_idx != -1 and len(values[row_idx]) > col_idx and values[row_idx][col_idx]:
                    url_count += 1
                else:
                    missing_urls.append(col_name)
            
            if url_count > 0:
                has_urls = True
                uuids_with_urls += 1
                logger.info(f"UUID {uuid} found in report (Topic: {topic})")
                logger.info(f"  - Has {url_count}/5 insight URLs")
                if missing_urls:
                    logger.info(f"  - Missing URLs: {', '.join(missing_urls)}")
            else:
                logger.warning(f"UUID {uuid} found in report (Topic: {topic}) but has NO insight URLs")
        else:
            logger.warning(f"UUID {uuid} NOT found in the report")
    
    logger.info(f"Summary: Found {found_uuids}/{len(UUIDS_TO_CHECK)} UUIDs in the report")
    logger.info(f"         {uuids_with_urls}/{found_uuids} UUIDs have at least one insight URL")

if __name__ == "__main__":
    check_uuids_in_report() 