#!/usr/bin/env python3
"""
Script to process manually transcribed .txt files in the MMM - Primary - June 2025 folder.

This script:
1. Scans the MMM - Primary - June 2025 folder for session subfolders
2. Looks for .txt files that contain manual transcriptions
3. Converts them to a format similar to VTT that can be used by the insight generation process
4. Updates the Zoom report with transcript information
"""

import os
import sys
import re
import logging
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

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

async def process_manual_transcripts():
    """Process manually transcribed .txt files in the MMM - Primary - June 2025 folder."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Drive service
    drive_service = get_drive_service()
    
    # Get the MMM - Primary - June 2025 folder ID
    query = f"name = 'MMM - Primary - June 2025' and mimeType = 'application/vnd.google-apps.folder' and '{config.GOOGLE_DRIVE_ROOT_FOLDER}' in parents and trashed = false"
    
    if config.USE_SHARED_DRIVE:
        results = drive_service.files().list(
            q=query,
            corpora="drive",
            driveId=config.GOOGLE_SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
    else:
        results = drive_service.files().list(q=query).execute()
    
    if not results.get('files'):
        logger.error("MMM - Primary - June 2025 folder not found")
        return
    
    folder_id = results['files'][0]['id']
    logger.info(f"Found MMM - Primary - June 2025 folder with ID: {folder_id}")
    
    # Get all session subfolders
    query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    if config.USE_SHARED_DRIVE:
        results = drive_service.files().list(
            q=query,
            corpora="drive",
            driveId=config.GOOGLE_SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
    else:
        results = drive_service.files().list(q=query).execute()
    
    session_folders = results.get('files', [])
    logger.info(f"Found {len(session_folders)} session folders")
    
    # Process each session folder
    for session_folder in session_folders:
        folder_name = session_folder['name']
        folder_id = session_folder['id']
        
        logger.info(f"Processing session folder: {folder_name}")
        
        # Look for .txt files
        query = f"'{folder_id}' in parents and mimeType = 'text/plain' and name ends with '.txt' and trashed = false"
        
        if config.USE_SHARED_DRIVE:
            results = drive_service.files().list(
                q=query,
                corpora="drive",
                driveId=config.GOOGLE_SHARED_DRIVE_ID,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
        else:
            results = drive_service.files().list(q=query).execute()
        
        txt_files = results.get('files', [])
        
        if not txt_files:
            logger.info(f"No .txt files found in {folder_name}")
            continue
        
        for txt_file in txt_files:
            file_name = txt_file['name']
            file_id = txt_file['id']
            
            logger.info(f"Processing .txt file: {file_name}")
            
            # Download the .txt file
            if config.USE_SHARED_DRIVE:
                request = drive_service.files().get_media(
                    fileId=file_id,
                    supportsAllDrives=True
                )
            else:
                request = drive_service.files().get_media(fileId=file_id)
            
            content = request.execute()
            
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            
            # Convert to VTT format
            vtt_content = convert_to_vtt(content)
            
            # Create a new VTT file
            vtt_file_name = file_name.replace('.txt', '.vtt')
            
            file_metadata = {
                'name': vtt_file_name,
                'parents': [folder_id],
                'mimeType': 'text/vtt'
            }
            
            # Create a temporary file
            temp_path = os.path.join("temp", vtt_file_name)
            os.makedirs("temp", exist_ok=True)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(vtt_content)
            
            # Upload the VTT file
            from googleapiclient.http import MediaFileUpload
            
            media = MediaFileUpload(
                temp_path,
                mimetype='text/vtt',
                resumable=True
            )
            
            if config.USE_SHARED_DRIVE:
                file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink',
                    supportsAllDrives=True
                ).execute()
            else:
                file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink'
                ).execute()
            
            logger.info(f"Created VTT file: {vtt_file_name} with ID: {file.get('id')}")
            
            # Update the Zoom report with transcript information
            await update_report_with_transcript(folder_name, file.get('webViewLink'))
            
            # Clean up temporary file
            os.remove(temp_path)

def convert_to_vtt(text_content: str) -> str:
    """
    Convert plain text content to VTT format.
    
    Args:
        text_content: Plain text content
        
    Returns:
        VTT formatted content
    """
    lines = text_content.split('\n')
    
    # Create VTT header
    vtt_content = "WEBVTT\n\n"
    
    # Add timestamps and captions
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        
        # Create a simple timestamp (1 minute per line)
        start_time = format_timestamp(i * 60)
        end_time = format_timestamp((i + 1) * 60)
        
        vtt_content += f"{i + 1}\n"
        vtt_content += f"{start_time} --> {end_time}\n"
        vtt_content += f"{line.strip()}\n\n"
    
    return vtt_content

def format_timestamp(seconds: int) -> str:
    """
    Format seconds as HH:MM:SS.000 timestamp.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.000"

async def update_report_with_transcript(folder_name: str, transcript_url: str):
    """
    Update the Zoom report with transcript information.
    
    Args:
        folder_name: Name of the session folder
        transcript_url: URL to the transcript file
    """
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        logger.error("Error: ZOOM_REPORT_ID not found in environment variables.")
        return
    
    # Initialize Google Sheets service
    sheets_service = get_sheets_service()
    
    # Get sheet names first
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    
    if not sheets:
        logger.error("No sheets found in the spreadsheet.")
        return
        
    # Use the first sheet's title
    sheet_title = sheets[0]['properties']['title']
    
    # Get the spreadsheet values
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=report_id,
        range=f"{sheet_title}"
    ).execute()
    
    values = result.get('values', [])
    if not values:
        logger.error("No data found in report.")
        return
    
    # Convert to DataFrame for easier analysis
    headers = values[0]
    data = values[1:] if len(values) > 1 else []
    df = pd.DataFrame(data, columns=headers)
    
    # Find the row for this session
    matching_rows = []
    
    for i, row in df.iterrows():
        topic = row.get("Meeting Topic", "")
        
        # Check if the folder name contains the topic
        if topic and topic in folder_name:
            matching_rows.append((i, row))
    
    if not matching_rows:
        logger.warning(f"No matching row found for session: {folder_name}")
        return
    
    if len(matching_rows) > 1:
        logger.warning(f"Multiple matching rows found for session: {folder_name}")
    
    # Update the first matching row
    row_index, row = matching_rows[0]
    
    # Update the Has Transcript and Transcript URL fields
    transcript_col_index = headers.index("Has Transcript") if "Has Transcript" in headers else -1
    url_col_index = headers.index("Transcript URL") if "Transcript URL" in headers else -1
    
    if transcript_col_index >= 0 and url_col_index >= 0:
        # Update the spreadsheet
        sheets_service.spreadsheets().values().update(
            spreadsheetId=report_id,
            range=f"{sheet_title}!{chr(65+transcript_col_index)}{row_index+2}",
            valueInputOption="USER_ENTERED",
            body={"values": [["TRUE"]]}
        ).execute()
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=report_id,
            range=f"{sheet_title}!{chr(65+url_col_index)}{row_index+2}",
            valueInputOption="USER_ENTERED",
            body={"values": [[transcript_url]]}
        ).execute()
        
        logger.info(f"Updated transcript information for session: {folder_name}")
    else:
        logger.warning(f"Could not find Has Transcript or Transcript URL columns in the report")

async def main():
    """Main function."""
    await process_manual_transcripts()

if __name__ == "__main__":
    asyncio.run(main()) 