#!/usr/bin/env python
"""
Script to process recordings stored in Google Drive and generate insights.
This script will:
1. Connect to Google Drive
2. Find all course folders
3. Find all session folders with unprocessed transcripts
4. For each transcript, generate insights
5. Save insights in the same folder

Logging:
- All operations are logged to both console and a timestamped log file in the 'logs' directory
- Log level can be controlled with the --log-level parameter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Use DEBUG level to see detailed API interactions
"""

import os
import sys
import argparse
import tempfile
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import time

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import AnalysisRequest, AnalysisResult
from app.services.analysis import generate_analysis
from app.services.drive_manager import upload_file
import config

# Set up logging with timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"drive_processing_{timestamp}.log")

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
        logger.debug(f"Using credentials file: {credentials_file}")
        logger.debug(f"Using scopes: {scopes}")
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        
        self.service = build("drive", "v3", credentials=credentials)
        self.root_folder_id = config.GOOGLE_DRIVE_ROOT_FOLDER
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
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
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
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                    
            logger.debug(f"File downloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
            
    def create_marker_file(self, folder_id: str, marker_name: str = ".processed") -> bool:
        """
        Create a marker file to indicate processing is complete.
        
        Args:
            folder_id: ID of the folder
            marker_name: Name of the marker file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Creating marker file in folder: {folder_id}")
            file_metadata = {
                "name": marker_name,
                "parents": [folder_id],
                "mimeType": "text/plain"
            }
            
            result = self.service.files().create(
                body=file_metadata,
                fields="id"
            ).execute()
            
            logger.debug(f"Marker file created with ID: {result.get('id')}")
            return True
        except Exception as e:
            logger.error(f"Error creating marker file: {e}")
            return False

async def process_session_folder(drive_manager: DriveManager, folder_id: str, folder_name: str, temp_dir: str, retry_failed: bool = False, backoff_time: int = 60) -> bool:
    """
    Process a session folder by generating insights for the transcript.
    
    Args:
        drive_manager: Drive manager instance
        folder_id: ID of the session folder
        folder_name: Name of the session folder
        temp_dir: Directory for temporary files
        retry_failed: Whether to retry previously failed folders
        backoff_time: Time to wait before retrying after rate limit (seconds)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if already processed
        files = drive_manager.list_files(folder_id)
        file_names = [file["name"] for file in files]
        
        # Check for marker file indicating successful processing
        if ".processed" in file_names and not retry_failed:
            logger.info(f"Folder already processed: {folder_name}")
            return True
            
        # Check for marker file indicating failed processing
        if ".processing_failed" in file_names and not retry_failed:
            logger.info(f"Folder previously failed processing and retry_failed is False: {folder_name}")
            return False
            
        # Find transcript file
        logger.debug(f"Looking for transcript file in folder")
        transcript_file = None
        chat_file = None
        metadata_file = None
        
        for file in files:
            if file["name"].lower().endswith(".vtt") or file["name"] == "transcript.vtt":
                transcript_file = file
            elif file["name"] == "chat_log.txt":
                chat_file = file
            elif file["name"] == "meeting_metadata.json":
                metadata_file = file
                
        if not transcript_file:
            logger.warning(f"No transcript found in folder: {folder_name}")
            return False
            
        # Download transcript
        transcript_path = os.path.join(temp_dir, "transcript.vtt")
        success = drive_manager.download_file(transcript_file["id"], transcript_path)
        if not success:
            logger.error(f"Failed to download transcript from folder: {folder_name}")
            return False
            
        # Download chat log if available
        chat_log_path = None
        if chat_file:
            chat_log_path = os.path.join(temp_dir, "chat_log.txt")
            success = drive_manager.download_file(chat_file["id"], chat_log_path)
            if not success:
                logger.warning(f"Failed to download chat log from folder: {folder_name}")
                chat_log_path = None
            else:
                logger.info(f"Chat log downloaded for additional context")
            
        # Download metadata if available
        metadata = {}
        if metadata_file:
            metadata_path = os.path.join(temp_dir, "metadata.json")
            success = drive_manager.download_file(metadata_file["id"], metadata_path)
            if success:
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    logger.debug(f"Loaded metadata for meeting: {metadata.get('topic', folder_name)}")
                    os.unlink(metadata_path)
                except Exception as e:
                    logger.error(f"Error loading metadata: {e}")
            
        # Check which analyses need to be generated
        analysis_types_to_generate = []
        
        # Check for existing analysis files
        analysis_files = {
            "executive_summary": "executive_summary.md",
            "pedagogical_analysis": "pedagogical_analysis.md",
            "aha_moments": "aha_moments.md",
            "engagement_analysis": "engagement_metrics.json",
            "concise_summary": "concise_summary.md"
        }
        
        for analysis_type, file_name in analysis_files.items():
            if file_name not in file_names:
                if analysis_type != "concise_summary":  # We'll handle concise summary separately
                    analysis_types_to_generate.append(analysis_type)
                    logger.info(f"Need to generate {analysis_type} (file {file_name} not found)")
            else:
                logger.info(f"Skipping {analysis_type} generation as {file_name} already exists")
        
        # If no analyses need to be generated, we can skip the API call
        if not analysis_types_to_generate:
            logger.info(f"All analysis files already exist, skipping generation")
            return True
        
        # Generate analysis
        logger.info(f"Generating analysis for transcript: {', '.join(analysis_types_to_generate)}")
        request = AnalysisRequest(
            transcript_path=transcript_path,
            chat_log_path=chat_log_path,
            analysis_types=analysis_types_to_generate,
            participant_school_mapping={}
        )
        
        try:
            result = await generate_analysis(request)
            logger.info(f"Analysis generation completed")
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error generating analysis: {error_message}")
            
            # Handle rate limiting errors
            if "rate_limit_error" in error_message or "429" in error_message:
                logger.warning(f"Rate limit exceeded. Waiting {backoff_time} seconds before retrying...")
                
                # Create a temporary marker to indicate processing was attempted but failed
                drive_manager.create_marker_file(folder_id, ".processing_failed")
                
                # Wait for backoff time
                time.sleep(backoff_time)
                return False
            elif "overloaded_error" in error_message or "529" in error_message:
                logger.warning(f"Claude API overloaded. Waiting {backoff_time} seconds before retrying...")
                
                # Create a temporary marker to indicate processing was attempted but failed
                drive_manager.create_marker_file(folder_id, ".processing_failed")
                
                # Wait for backoff time
                time.sleep(backoff_time)
                return False
            else:
                # For other errors, mark as failed and continue
                drive_manager.create_marker_file(folder_id, ".processing_failed")
                return False
        
        # Upload results to Drive
        logger.info(f"Uploading analysis results to Drive")
        
        if result.executive_summary:
            logger.debug(f"Uploading executive summary")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(result.executive_summary)
                exec_summary_path = f.name
                
            await upload_file(
                file_path=exec_summary_path,
                folder_id=folder_id,
                file_name="executive_summary.md",
                mime_type="text/markdown"
            )
            
            # Generate concise summary if it doesn't exist
            if "concise_summary.md" not in file_names:
                logger.debug(f"Generating concise summary from executive summary")
                try:
                    # Import the function here to avoid circular imports
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from generate_concise_summary import generate_concise_summary
                    
                    # Generate concise summary using the executive summary
                    concise_summary = await generate_concise_summary(existing_summary=result.executive_summary)
                    
                    # Upload concise summary
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                        f.write(concise_summary)
                        concise_summary_path = f.name
                        
                    await upload_file(
                        file_path=concise_summary_path,
                        folder_id=folder_id,
                        file_name="concise_summary.md",
                        mime_type="text/markdown"
                    )
                    os.unlink(concise_summary_path)
                    logger.info(f"Generated and uploaded concise summary")
                except Exception as e:
                    logger.error(f"Error generating concise summary: {e}")
            
            os.unlink(exec_summary_path)
        
        if result.pedagogical_analysis:
            logger.debug(f"Uploading pedagogical analysis")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(result.pedagogical_analysis)
                pedagogical_path = f.name
                
            await upload_file(
                file_path=pedagogical_path,
                folder_id=folder_id,
                file_name="pedagogical_analysis.md",
                mime_type="text/markdown"
            )
            os.unlink(pedagogical_path)
            
        if result.aha_moments:
            logger.debug(f"Uploading aha moments")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(result.aha_moments)
                aha_path = f.name
                
            await upload_file(
                file_path=aha_path,
                folder_id=folder_id,
                file_name="aha_moments.md",
                mime_type="text/markdown"
            )
            os.unlink(aha_path)
            
        if result.engagement_metrics:
            logger.debug(f"Uploading engagement metrics")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(result.engagement_metrics, f, indent=2)
                engagement_path = f.name
                
            await upload_file(
                file_path=engagement_path,
                folder_id=folder_id,
                file_name="engagement_metrics.json",
                mime_type="application/json"
            )
            os.unlink(engagement_path)
        
        # Create marker file
        logger.debug(f"Creating marker file to indicate processing is complete")
        drive_manager.create_marker_file(folder_id)
        
        # Clean up
        logger.debug(f"Cleaning up temporary files")
        os.unlink(transcript_path)
        if chat_log_path and os.path.exists(chat_log_path):
            os.unlink(chat_log_path)
        
        logger.info(f"Successfully processed folder: {folder_name}")
        return True
    except Exception as e:
        logger.error(f"Error processing folder {folder_name}: {e}")
        return False

async def process_course_folder(drive_manager: DriveManager, folder_id: str, folder_name: str, temp_dir: str) -> int:
    """
    Process a course folder by finding and processing all session folders.
    
    Args:
        drive_manager: Drive manager instance
        folder_id: ID of the course folder
        folder_name: Name of the course folder
        temp_dir: Directory for temporary files
        
    Returns:
        Number of successfully processed sessions
    """
    logger.info(f"Processing course folder: {folder_name}")
    
    # List all session folders
    session_folders = drive_manager.list_folders(folder_id)
    
    processed_count = 0
    for folder in session_folders:
        logger.info(f"Processing session folder: {folder['name']}")
        success = await process_session_folder(drive_manager, folder["id"], folder["name"], temp_dir)
        if success:
            processed_count += 1
            
    return processed_count

async def main():
    """Main function to process recordings in Drive."""
    parser = argparse.ArgumentParser(description="Process recordings in Google Drive")
    parser.add_argument("--temp-dir", type=str, default="./temp", help="Temporary directory for downloads")
    parser.add_argument("--course", type=str, help="Process only a specific course")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="Set the logging level")
    parser.add_argument("--retry-failed", action="store_true", help="Retry previously failed folders")
    parser.add_argument("--backoff-time", type=int, default=60, 
                        help="Time to wait before retrying after rate limit (seconds)")
    
    args = parser.parse_args()
    
    # Set logging level based on command-line argument
    logger.setLevel(getattr(logging, args.log_level))
    
    # Create temp directory
    os.makedirs(args.temp_dir, exist_ok=True)
    
    logger.info("Starting Drive processing")
    
    # Initialize Drive manager
    drive_manager = DriveManager()
    
    # Process all course folders
    course_folders = drive_manager.list_folders(drive_manager.root_folder_id)
    
    for course_folder in course_folders:
        course_name = course_folder["name"]
        
        # Skip if not the specified course
        if args.course and course_name != args.course:
            logger.debug(f"Skipping course folder: {course_name}")
            continue
            
        logger.info(f"Processing course folder: {course_name}")
        
        # Get all session folders
        session_folders = drive_manager.list_folders(course_folder["id"])
        
        for session_folder in session_folders:
            session_name = session_folder["name"]
            logger.info(f"Processing session folder: {session_name}")
            
            # Process session folder
            await process_session_folder(
                drive_manager=drive_manager,
                folder_id=session_folder["id"],
                folder_name=session_name,
                temp_dir=args.temp_dir,
                retry_failed=args.retry_failed,
                backoff_time=args.backoff_time
            )
            
    logger.info("Drive processing completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 