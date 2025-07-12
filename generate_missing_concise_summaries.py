#!/usr/bin/env python
"""
Script to find all executive summaries and generate corresponding concise summaries.
This script will:
1. Connect to Google Drive
2. Find all executive_summary.md files
3. For each file, check if a corresponding concise_summary.md exists
4. If not, download the executive summary, generate a concise summary, and upload it
5. Update the Zoom report with the new concise summary URLs
"""

import os
import sys
import tempfile
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import pandas as pd

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generate_concise_summary import generate_concise_summary
import config

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"concise_summary_generation_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_filename}")

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
        self.root_folder_id = config.GOOGLE_DRIVE_ROOT_FOLDER
        logger.info(f"Drive Manager initialized with root folder ID: {self.root_folder_id}")
    
    def find_executive_summaries(self) -> List[Dict]:
        """
        Find all executive summary files in Drive.
        
        Returns:
            List of file objects
        """
        query = f"name = 'executive_summary.md' and trashed = false"
        logger.info(f"Searching for executive summary files")
        
        results = []
        page_token = None
        
        while True:
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, parents)",
                pageToken=page_token
            ).execute()
            
            page_results = response.get("files", [])
            results.extend(page_results)
            
            page_token = response.get("nextPageToken")
            
            if not page_token:
                break
                
        logger.info(f"Found {len(results)} executive summary files")
        return results
    
    def check_concise_summary_exists(self, parent_id: str) -> bool:
        """
        Check if a concise summary exists in the folder.
        
        Args:
            parent_id: ID of the parent folder
            
        Returns:
            True if exists, False otherwise
        """
        query = f"name = 'concise_summary.md' and '{parent_id}' in parents and trashed = false"
        
        response = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)"
        ).execute()
        
        return len(response.get("files", [])) > 0
    
    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file from Drive.
        
        Args:
            file_id: ID of the file to download
            output_path: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Downloading file with ID: {file_id} to {output_path}")
            request = self.service.files().get_media(fileId=file_id)
            
            with open(output_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    
            logger.debug(f"File downloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def upload_file(self, file_path: str, folder_id: str, file_name: str, mime_type: str) -> Optional[str]:
        """
        Upload a file to Drive.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to
            file_name: Name to give the file
            mime_type: MIME type of the file
            
        Returns:
            ID of the uploaded file, or None if failed
        """
        try:
            logger.debug(f"Uploading file {file_path} to folder {folder_id}")
            
            file_metadata = {
                "name": file_name,
                "parents": [folder_id],
                "mimeType": mime_type
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink"
            ).execute()
            
            logger.debug(f"File uploaded with ID: {file.get('id')}")
            return file.get("id"), file.get("webViewLink")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None, None
    
    def get_folder_name(self, folder_id: str) -> str:
        """
        Get the name of a folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            Name of the folder
        """
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="name"
            ).execute()
            
            return folder.get("name", "Unknown folder")
        except Exception as e:
            logger.error(f"Error getting folder name: {e}")
            return "Unknown folder"

async def process_executive_summary(drive_manager: DriveManager, file: Dict, temp_dir: str) -> Optional[Dict]:
    """
    Process an executive summary file to generate a concise summary.
    
    Args:
        drive_manager: Drive manager instance
        file: Executive summary file object
        temp_dir: Directory for temporary files
        
    Returns:
        Dictionary with session folder ID and concise summary URL, or None if failed
    """
    try:
        file_id = file["id"]
        parent_id = file["parents"][0]
        
        # Check if concise summary already exists
        if drive_manager.check_concise_summary_exists(parent_id):
            logger.info(f"Concise summary already exists for folder {parent_id}")
            return None
        
        # Get folder name for logging
        folder_name = drive_manager.get_folder_name(parent_id)
        logger.info(f"Processing executive summary in folder: {folder_name}")
        
        # Download executive summary
        exec_summary_path = os.path.join(temp_dir, "executive_summary.md")
        success = drive_manager.download_file(file_id, exec_summary_path)
        if not success:
            logger.error(f"Failed to download executive summary from folder: {folder_name}")
            return None
        
        # Read executive summary content
        with open(exec_summary_path, "r") as f:
            exec_summary_content = f.read()
        
        # Generate concise summary
        logger.info(f"Generating concise summary from executive summary")
        concise_summary = await generate_concise_summary(existing_summary=exec_summary_content)
        
        if not concise_summary:
            logger.error(f"Failed to generate concise summary for folder: {folder_name}")
            return None
        
        # Upload concise summary
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(concise_summary)
            concise_summary_path = f.name
            
        file_id, web_view_link = drive_manager.upload_file(
            file_path=concise_summary_path,
            folder_id=parent_id,
            file_name="concise_summary.md",
            mime_type="text/markdown"
        )
        
        # Clean up
        os.unlink(exec_summary_path)
        os.unlink(concise_summary_path)
        
        if not file_id:
            logger.error(f"Failed to upload concise summary for folder: {folder_name}")
            return None
        
        logger.info(f"Successfully generated and uploaded concise summary for folder: {folder_name}")
        return {
            "session_folder_id": parent_id,
            "folder_name": folder_name,
            "concise_summary_url": web_view_link
        }
    except Exception as e:
        logger.error(f"Error processing executive summary: {e}")
        return None

def update_zoom_report(results: List[Dict], temp_dir: str):
    """
    Update the Zoom report with concise summary URLs.
    
    Args:
        results: List of results from processing executive summaries
        temp_dir: Directory for temporary files
    """
    try:
        # Check if report exists
        report_path = os.path.join(temp_dir, "zoom_recordings_report.csv")
        if not os.path.exists(report_path):
            logger.warning(f"Zoom report not found at {report_path}")
            return
        
        # Read the report
        df = pd.read_csv(report_path)
        
        # Ensure password and Drive Video URL columns are removed
        if "Meeting Password" in df.columns:
            df = df.drop(columns=["Meeting Password"])
            logger.info("Removed Meeting Password column from the report")
            
        if "Drive Video URL" in df.columns:
            df = df.drop(columns=["Drive Video URL"])
            logger.info("Removed Drive Video URL column from the report")
        
        # Get Drive service
        credentials = service_account.Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive_service = build("drive", "v3", credentials=credentials)
        
        # Update concise summary URLs
        updated_count = 0
        for result in results:
            if not result:
                continue
                
            folder_name = result["folder_name"]
            concise_summary_url = result["concise_summary_url"]
            
            # Find matching rows in the report
            for i, row in df.iterrows():
                # Check if this row corresponds to the folder
                if folder_name in str(row["Meeting Topic"]):
                    df.at[i, "Concise Summary URL"] = concise_summary_url
                    updated_count += 1
                    logger.info(f"Updated concise summary URL for meeting: {row['Meeting Topic']}")
        
        if updated_count > 0:
            # Save the updated report with proper URL formatting
            with pd.option_context('display.max_colwidth', None):
                df.to_csv(report_path, index=False)
            logger.info(f"Saved updated report with {updated_count} concise summary URLs")
            
            # Upload to Google Drive
            report_name = "Zoom Recordings Report"
            query = f"name = '{report_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{config.GOOGLE_DRIVE_ROOT_FOLDER}' in parents and trashed = false"
            results = drive_service.files().list(q=query).execute()
            
            if results.get('files'):
                file_id = results['files'][0]['id']
                
                # Create media
                media = MediaFileUpload(
                    report_path,
                    mimetype='text/csv',
                    resumable=True
                )
                
                # Update file content
                logger.info(f"Updating existing report with ID: {file_id}")
                file = drive_service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                
                # Get the webViewLink
                file = drive_service.files().get(
                    fileId=file_id,
                    fields='webViewLink'
                ).execute()
                
                logger.info(f"Report updated successfully")
                logger.info(f"Report can be viewed at: {file.get('webViewLink')}")
        else:
            logger.info("No changes made to the report")
    except Exception as e:
        logger.error(f"Error updating Zoom report: {e}")

async def main():
    """Main function to generate missing concise summaries."""
    parser = argparse.ArgumentParser(description="Generate missing concise summaries")
    parser.add_argument("--temp-dir", type=str, default="./temp", help="Temporary directory for downloads")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="Set the logging level")
    parser.add_argument("--batch-size", type=int, default=5, 
                        help="Number of summaries to process in parallel (to avoid API rate limits)")
    parser.add_argument("--delay", type=int, default=60, 
                        help="Delay between batches in seconds (to avoid API rate limits)")
    
    args = parser.parse_args()
    
    # Set logging level based on command-line argument
    logger.setLevel(getattr(logging, args.log_level))
    
    # Create temp directory
    os.makedirs(args.temp_dir, exist_ok=True)
    
    logger.info("Starting concise summary generation")
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Find all executive summaries
    exec_summaries = drive_manager.find_executive_summaries()
    
    # Process executive summaries in batches to avoid API rate limits
    results = []
    for i in range(0, len(exec_summaries), args.batch_size):
        batch = exec_summaries[i:i+args.batch_size]
        logger.info(f"Processing batch {i//args.batch_size + 1} of {(len(exec_summaries) + args.batch_size - 1) // args.batch_size}")
        
        # Process batch in parallel
        batch_tasks = [process_executive_summary(drive_manager, file, args.temp_dir) for file in batch]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Add non-None results to the list
        results.extend([r for r in batch_results if r])
        
        # Delay between batches to avoid API rate limits
        if i + args.batch_size < len(exec_summaries):
            logger.info(f"Waiting {args.delay} seconds before next batch to avoid API rate limits")
            await asyncio.sleep(args.delay)
    
    # Update the Zoom report with the new concise summary URLs
    update_zoom_report(results, args.temp_dir)
    
    logger.info(f"Concise summary generation completed. Generated {len(results)} new concise summaries")

if __name__ == "__main__":
    import argparse
    asyncio.run(main()) 