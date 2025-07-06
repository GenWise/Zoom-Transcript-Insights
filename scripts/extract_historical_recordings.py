#!/usr/bin/env python
"""
Script to extract historical recordings from Zoom and save them to Google Drive.
This script will:
1. Authenticate with Zoom API
2. Fetch list of past recordings within a date range
3. Download VTT transcripts for each recording
4. Create appropriate folder structure in Google Drive
5. Upload transcripts to Google Drive

Logging:
- All operations are logged to both console and a timestamped log file in the 'logs' directory
- Log level can be controlled with the --log-level parameter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Use DEBUG level to see full OAuth scopes and detailed API interactions
"""

import os
import sys
import argparse
import requests
import json
import time
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
import re
import pandas as pd
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.drive_manager import create_folder_structure, upload_file, get_drive_service
import config

# Set up logging with timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"zoom_extraction_{timestamp}.log")

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

class ZoomClient:
    """Client for interacting with Zoom API."""
    
    def __init__(self):
        """Initialize the Zoom client."""
        self.client_id = config.ZOOM_CLIENT_ID
        self.client_secret = config.ZOOM_CLIENT_SECRET
        self.account_id = config.ZOOM_ACCOUNT_ID
        self.base_url = config.ZOOM_BASE_URL
        self.access_token = None
        self.token_expiry = 0
        
        logger.info("Zoom Configuration:")
        logger.info(f"Client ID: *****************{self.client_id[-4:]}")
        logger.info(f"Client Secret: ********")
        logger.info(f"Account ID: ******************{self.account_id[-4:]}")
        logger.info(f"Base URL: {self.base_url}")
        
    def get_access_token(self) -> str:
        """Get an access token from Zoom API."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token
            
        url = "https://zoom.us/oauth/token"
        auth = (self.client_id, self.client_secret)
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }
        
        logger.info(f"Requesting access token from {url}")
        logger.info(f"Request data: {json.dumps(data)}")
        
        try:
            response = requests.post(url, auth=auth, data=data)
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.text}")
                return None
                
            result = response.json()
            self.access_token = result["access_token"]
            self.token_expiry = time.time() + result["expires_in"] - 60  # Subtract 60 seconds for safety
            
            logger.info("Access token received")
            logger.info(f"Token type: {result['token_type']}")
            logger.info(f"Expires in: {result['expires_in']} seconds")
            
            # Log scopes based on log level
            scopes = result.get("scope", "").split(" ")
            if logger.level <= logging.DEBUG:
                logger.debug(f"OAuth scopes: {', '.join(scopes)}")
            else:
                logger.info(f"OAuth scopes received (use --log-level=DEBUG to see full scopes)")
                
            return self.access_token
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
            
    def download_file(self, url: str, output_path: str) -> bool:
        """
        Download a file from a URL using the access token.
        
        Args:
            url: URL to download from
            output_path: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        if not url:
            logger.warning("No URL provided for download")
            return False
            
        access_token = self.get_access_token()
        if not access_token:
            logger.error("No access token available for download")
            return False
            
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            logger.debug(f"Downloading file from URL: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to download file: {response.status_code} - {response.text}")
                return False
                
            with open(output_path, "wb") as f:
                f.write(response.content)
                
            logger.debug(f"File downloaded to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def list_users(self) -> List[Dict]:
        """
        List users in the Zoom account.
        
        Returns:
            List of user objects
        """
        url = f"{self.base_url}/users"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        params = {
            "status": "active",
            "page_size": 100
        }
        
        logger.info(f"Listing users from {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Failed to list users: {response.text}")
                raise Exception(f"Failed to list users: {response.text}")
                
            data = response.json()
            users = data.get("users", [])
            logger.info(f"Found {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise
        
    def get_recordings(self, start_date: str, end_date: str, user_email: Optional[str] = None, page_size: int = 100) -> List[Dict]:
        """
        Get recordings from Zoom API.
        
        Args:
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            user_email: Optional email of specific user to get recordings for
            page_size: Number of recordings per page
            
        Returns:
            List of recording objects
        """
        recordings = []
        
        # If specific user is provided, get recordings only for that user
        if user_email:
            logger.info(f"Getting recordings for specific user: {user_email}")
            user_id = self._get_user_id_by_email(user_email)
            if user_id:
                user_recordings = self._get_user_recordings(user_id, start_date, end_date, page_size)
                recordings.extend(user_recordings)
            return recordings
        
        # First, try to use the account-level endpoint
        try:
            logger.info(f"Attempting to get recordings from account-level endpoint")
            account_recordings = self._get_account_recordings(start_date, end_date, page_size)
            if account_recordings:
                logger.info(f"Successfully retrieved recordings from account-level endpoint")
                return account_recordings
        except Exception as e:
            logger.warning(f"Failed to get recordings from account-level endpoint: {str(e)}")
            logger.info("Falling back to user-level endpoint")
        
        # If account-level endpoint fails, try user-level endpoint
        try:
            # Get list of users
            users = self.list_users()
            
            # Get recordings for each user
            for user in users:
                user_id = user.get("id")
                if not user_id:
                    continue
                
                logger.info(f"Getting recordings for user {user.get('email', user_id)}")
                user_recordings = self._get_user_recordings(user_id, start_date, end_date, page_size)
                recordings.extend(user_recordings)
                
            return recordings
        except Exception as e:
            logger.error(f"Error getting recordings: {str(e)}")
            raise
    
    def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """
        Get user ID by email.
        
        Args:
            email: User email
            
        Returns:
            User ID if found, None otherwise
        """
        url = f"{self.base_url}/users"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        params = {
            "email": email,
            "status": "active"
        }
        
        logger.info(f"Looking up user ID for email: {email}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Failed to get user by email: {response.text}")
                return None
                
            data = response.json()
            users = data.get("users", [])
            
            if not users:
                logger.warning(f"No user found with email: {email}")
                return None
                
            user_id = users[0].get("id")
            logger.info(f"Found user ID: {user_id} for email: {email}")
            return user_id
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def _get_account_recordings(self, start_date: str, end_date: str, page_size: int = 100) -> List[Dict]:
        """
        Get recordings from account-level endpoint.
        
        Args:
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            page_size: Number of recordings per page
            
        Returns:
            List of recording objects
        """
        recordings = []
        next_page_token = ""
        
        logger.info(f"Getting account recordings from {start_date} to {end_date}")
        
        while True:
            url = f"{self.base_url}/accounts/{self.account_id}/recordings"
            params = {
                "from": start_date,
                "to": end_date,
                "page_size": page_size,
                "next_page_token": next_page_token
            }
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Making request to {url}")
            logger.info(f"Request parameters: {json.dumps(params)}")
            
            response = requests.get(url, params=params, headers=headers)
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Failed to get account recordings: {response.text}")
                raise Exception(f"Failed to get account recordings: {response.text}")
                
            data = response.json()
            meetings = data.get("meetings", [])
            logger.info(f"Retrieved {len(meetings)} recordings")
            
            recordings.extend(meetings)
            
            next_page_token = data.get("next_page_token", "")
            if not next_page_token:
                break
                
        return recordings
    
    def get_user(self, user_id: str) -> Dict:
        """
        Get user details from Zoom API.
        
        Args:
            user_id: User ID
            
        Returns:
            User details as dictionary
        """
        url = f"{self.base_url}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting user details for {user_id}")
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get user details: {response.text}")
                return {}
        except Exception as e:
            logger.warning(f"Error getting user details: {e}")
            return {}
    
    def _get_user_recordings(self, user_id: str, start_date: str, end_date: str, page_size: int = 100) -> List[Dict]:
        """
        Get recordings for a specific user.
        
        Args:
            user_id: User ID
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            page_size: Number of recordings per page
            
        Returns:
            List of recording objects
        """
        recordings = []
        next_page_token = ""
        
        logger.info(f"Getting user recordings from {start_date} to {end_date} for user {user_id}")
        
        while True:
            url = f"{self.base_url}/users/{user_id}/recordings"
            params = {
                "from": start_date,
                "to": end_date,
                "page_size": page_size,
                "next_page_token": next_page_token
            }
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Making request to {url}")
            logger.info(f"Request parameters: {json.dumps(params)}")
            
            response = requests.get(url, params=params, headers=headers)
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"Failed to get user recordings: {response.text}")
                return []
                
            data = response.json()
            meetings = data.get("meetings", [])
            logger.info(f"Retrieved {len(meetings)} recordings for user {user_id}")
            
            recordings.extend(meetings)
            
            next_page_token = data.get("next_page_token", "")
            if not next_page_token:
                break
                
        return recordings
        
    def download_transcript(self, download_url: str, output_path: str) -> bool:
        """
        Download a transcript file from Zoom.
        
        Args:
            download_url: URL to download the transcript
            output_path: Path to save the transcript
            
        Returns:
            True if successful, False otherwise
        """
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}"
        }
        
        response = requests.get(download_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to download transcript: {response.text}")
            return False
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)
            
        return True

def parse_meeting_topic(topic: str) -> Dict[str, str]:
    """
    Parse the meeting topic to extract course name and session information.
    Accepts any format of meeting topic.
    
    Args:
        topic: Meeting topic
        
    Returns:
        Dictionary with course_name, session_number, and session_name
    """
    # Try to parse with expected format: "Course Name - Session X: Session Name"
    try:
        parts = topic.split(" - ")
        if len(parts) >= 2 and "Session" in parts[1]:
            course_name = parts[0].strip()
            session_part = parts[1].strip()
            
            # Try to extract session number
            session_number_match = re.search(r"Session\s*(\d+)", session_part)
            if session_number_match:
                session_number = int(session_number_match.group(1))
            else:
                session_number = 0
                
            # Try to extract session name
            if ":" in session_part:
                session_name = session_part.split(":", 1)[1].strip()
            else:
                session_name = session_part.replace(f"Session {session_number}", "").strip()
                
            return {
                "course_name": course_name,
                "session_number": session_number,
                "session_name": session_name
            }
    except (IndexError, ValueError, AttributeError):
        pass
        
    # If we can't parse with the expected format, use the topic as is
    logger.info(f"Using generic format for meeting topic: {topic}")
    return {
        "course_name": topic,
        "session_number": 0,
        "session_name": topic
    }

async def process_recording(recording: Dict, temp_dir: str) -> bool:
    """
    Process a recording by downloading transcript and uploading to Drive.
    
    Args:
        recording: Recording object from Zoom API
        temp_dir: Directory for temporary files
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract recording information
        topic = recording.get("topic", "Unknown")
        uuid = recording.get("uuid", "")
        meeting_id = recording.get("id", "")
        start_time = recording.get("start_time", "")
        
        # Parse start time to get date
        try:
            start_date = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            start_date = datetime.now().strftime("%Y-%m-%d")
            
        logger.info(f"Processing recording: {topic}")
        
        # Parse meeting topic
        parsed_topic = parse_meeting_topic(topic)
        course_name = parsed_topic["course_name"]
        session_number = parsed_topic["session_number"]
        session_name = parsed_topic["session_name"]
        
        # Find transcript file
        transcript_file = None
        video_files = []
        chat_file = None
        
        for file in recording.get("recording_files", []):
            if file.get("file_type") == "TRANSCRIPT":
                transcript_file = file
            elif file.get("file_type") in ["MP4", "M4A"]:
                video_files.append(file)
            elif file.get("file_type") == "CHAT":
                chat_file = file
        
        # Create folder structure in Drive
        folder_structure = await create_folder_structure(
            course_name=course_name,
            session_number=session_number,
            session_name=session_name,
            session_date=start_date
        )
        
        session_folder_id = folder_structure["session_folder_id"]
        
        # Check if this recording has already been processed
        drive_service = get_drive_service()
        query = f"name = 'meeting_metadata.json' and '{session_folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query).execute()
        
        if results.get('files'):
            logger.info(f"Metadata already exists for meeting: {topic}. Skipping processing.")
            return True
        
        # Initialize Zoom client
        client = ZoomClient()
        
        # Download and upload transcript if available
        if transcript_file:
            download_url = transcript_file.get("download_url")
            
            if download_url:
                # Download transcript
                transcript_path = os.path.join(temp_dir, "transcript.vtt")
                success = client.download_file(download_url, transcript_path)
                
                if success:
                    # Upload transcript to Drive
                    await upload_file(
                        file_path=transcript_path,
                        folder_id=session_folder_id,
                        file_name="transcript.vtt",
                        mime_type="text/vtt"
                    )
                    
                    # Clean up
                    os.unlink(transcript_path)
                else:
                    logger.warning(f"Failed to download transcript for meeting: {topic}")
            else:
                logger.warning(f"No download URL for transcript: {topic}")
        else:
            logger.warning(f"No transcript found for meeting: {topic}")
        
        # Download and upload chat log if available
        if chat_file:
            download_url = chat_file.get("download_url")
            
            if download_url:
                # Download chat log
                chat_path = os.path.join(temp_dir, "chat.txt")
                success = client.download_file(download_url, chat_path)
                
                if success:
                    # Upload chat log to Drive
                    await upload_file(
                        file_path=chat_path,
                        folder_id=session_folder_id,
                        file_name="chat_log.txt",
                        mime_type="text/plain"
                    )
                    
                    # Clean up
                    os.unlink(chat_path)
                else:
                    logger.warning(f"Failed to download chat log for meeting: {topic}")
            else:
                logger.warning(f"No download URL for chat log: {topic}")
        
        # Update meeting metadata
        await update_meeting_metadata(
            session_folder_id=session_folder_id,
            recording=recording,
            video_files=video_files,
            chat_file=chat_file
        )
        
        logger.info(f"Successfully processed recording: {topic}")
        return True
    except Exception as e:
        logger.error(f"Error processing recording: {e}")
        return False

async def update_meeting_metadata(session_folder_id: str, recording: Dict, video_files: List[Dict], chat_file: Dict = None) -> None:
    """
    Create or update metadata file with meeting information.
    
    Args:
        session_folder_id: ID of the session folder
        recording: Recording object from Zoom API
        video_files: List of video file objects
        chat_file: Chat file object (optional)
    """
    try:
        # Create metadata object
        metadata = {
            "meeting_id": recording.get("id", ""),
            "meeting_uuid": recording.get("uuid", ""),
            "topic": recording.get("topic", ""),
            "host_id": recording.get("host_id", ""),
            "host_email": recording.get("host_email", ""),
            "host_name": recording.get("host_name", "Unknown"),
            "start_time": recording.get("start_time", ""),
            "end_time": recording.get("end_time", ""),
            "duration": recording.get("duration", 0),
            "total_size": recording.get("total_size", 0),
            "recording_count": recording.get("recording_count", 0),
            "share_url": recording.get("share_url", ""),
            "password": recording.get("password", ""),
            "timezone": recording.get("timezone", ""),
            "videos": [],
            "chat_url": None,
            "extracted_at": datetime.now().isoformat(),
        }
        
        # Add video information
        for video in video_files:
            metadata["videos"].append({
                "id": video.get("id", ""),
                "file_type": video.get("file_type", ""),
                "file_size": video.get("file_size", 0),
                "play_url": video.get("play_url", ""),
                "download_url": video.get("download_url", ""),
                "recording_type": video.get("recording_type", ""),
                "recording_start": video.get("recording_start", ""),
                "recording_end": video.get("recording_end", ""),
            })
            
        # Add chat information if available
        if chat_file:
            metadata["chat_url"] = chat_file.get("download_url", "")
            
        # Save metadata to temporary file
        metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp", "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        # Upload metadata to Drive
        await upload_file(
            file_path=metadata_path,
            folder_id=session_folder_id,
            file_name="meeting_metadata.json",
            mime_type="application/json"
        )
        
        # Clean up
        os.unlink(metadata_path)
        
        logger.info(f"Updated meeting metadata")
    except Exception as e:
        logger.error(f"Error updating meeting metadata: {e}")

async def create_summary_report(recordings: List[Dict], temp_dir: str) -> None:
    """
    Create a summary report of all recordings in Google Sheets.
    
    Args:
        recordings: List of recording objects from Zoom API
        temp_dir: Directory for temporary files
    """
    logger.info("Creating summary report of extracted recordings")
    
    # Prepare data for the report
    report_data = []
    for recording in recordings:
        # Extract basic information
        topic = recording.get("topic", "Unknown")
        start_time = recording.get("start_time", "")
        duration = recording.get("duration", 0)
        
        # Extract user information
        user_name = recording.get("host_name", recording.get("host_id", "Unknown"))
        user_email = recording.get("host_email", "Unknown")
        
        # Try to get more detailed host information if available
        if user_name == "Unknown" or user_email == "Unknown":
            try:
                # If we have host_id but not name/email, try to get user details
                host_id = recording.get("host_id")
                if host_id:
                    # Create a local ZoomClient instance
                    from scripts.extract_historical_recordings import ZoomClient
                    local_zoom_client = ZoomClient()
                    user_details = local_zoom_client.get_user(host_id)
                    if user_details:
                        user_name = user_details.get("first_name", "") + " " + user_details.get("last_name", "")
                        user_email = user_details.get("email", user_email)
            except Exception as e:
                logger.warning(f"Could not get host details: {e}")
        
        # Check if transcript exists
        has_transcript = False
        transcript_url = None
        
        # Find video URL
        zoom_video_url = ""
        video_files = []
        
        for file in recording.get("recording_files", []):
            if file.get("file_type") == "TRANSCRIPT":
                has_transcript = True
                transcript_url = file.get("download_url", "")
            elif file.get("file_type") in ["MP4", "M4A"]:
                video_files.append(file)
                if not zoom_video_url and file.get("file_type") == "MP4":
                    zoom_video_url = file.get("play_url", "")
        
        # Calculate total size in MB and round to integer
        total_size_mb = int(sum(file.get("file_size", 0) for file in recording.get("recording_files", [])) / (1024 * 1024))
        
        # Parse meeting topic to get folder information
        parsed_topic = parse_meeting_topic(topic)
        course_name = parsed_topic["course_name"]
        session_number = parsed_topic["session_number"]
        session_name = parsed_topic["session_name"]
        
        # Parse start time to get date
        try:
            start_date = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            start_date = datetime.now().strftime("%Y-%m-%d")
        
        # Find the session folder in Drive to get analysis file links
        session_folder_id = None
        analysis_links = {
            "executive_summary_url": "",
            "pedagogical_analysis_url": "",
            "aha_moments_url": "",
            "engagement_metrics_url": "",
            "concise_summary_url": "",
            "drive_video_url": ""
        }
        
        try:
            # Get Drive service
            drive_service = get_drive_service()
            
            # Find course folder
            course_folder_name = f"{course_name}"
            query = f"name = '{course_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{config.GOOGLE_DRIVE_ROOT_FOLDER}' in parents and trashed = false"
            results = drive_service.files().list(q=query).execute()
            
            if results.get('files'):
                course_folder_id = results['files'][0]['id']
                
                # Find session folder
                session_folder_name = f"{course_name}_{start_date}"
                query = f"name = '{session_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{course_folder_id}' in parents and trashed = false"
                results = drive_service.files().list(q=query).execute()
                
                if not results.get('files'):
                    # Try with session number in the name
                    session_folder_name = f"Session_{session_number}_{session_name}_{start_date}"
                    query = f"name = '{session_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{course_folder_id}' in parents and trashed = false"
                    results = drive_service.files().list(q=query).execute()
                
                if results.get('files'):
                    session_folder_id = results['files'][0]['id']
                    
                    # Find analysis files
                    analysis_file_names = [
                        "executive_summary.md",
                        "pedagogical_analysis.md",
                        "aha_moments.md",
                        "engagement_metrics.json",
                        "concise_summary.md"
                    ]
                    
                    for file_name in analysis_file_names:
                        query = f"name = '{file_name}' and '{session_folder_id}' in parents and trashed = false"
                        results = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
                        
                        if results.get('files'):
                            file_key = file_name.split(".")[0] + "_url"
                            analysis_links[file_key] = results['files'][0].get('webViewLink', '')
                    
                    # Find video file in Drive
                    video_query = f"mimeType contains 'video/' and '{session_folder_id}' in parents and trashed = false"
                    video_results = drive_service.files().list(q=video_query, fields="files(id, name, webViewLink)").execute()
                    
                    if video_results.get('files'):
                        analysis_links["drive_video_url"] = video_results['files'][0].get('webViewLink', '')
        except Exception as e:
            logger.error(f"Error finding analysis files for {topic}: {e}")
        
        # Add to report data
        report_data.append({
            "Meeting Topic": topic,
            "Host Name": user_name,
            "Host Email": user_email,
            "Start Time": start_time,
            "Duration (minutes)": duration,
            "Has Transcript": has_transcript,
            "Transcript URL": transcript_url if has_transcript else "N/A",
            "Meeting UUID": recording.get("uuid", ""),
            "Meeting ID": recording.get("id", ""),
            "Size (MB)": total_size_mb,
            "Meeting Password": recording.get("password", ""),
            "Zoom Video URL": zoom_video_url,
            "Drive Video URL": analysis_links["drive_video_url"],
            "Executive Summary URL": analysis_links["executive_summary_url"],
            "Pedagogical Analysis URL": analysis_links["pedagogical_analysis_url"],
            "Aha Moments URL": analysis_links["aha_moments_url"],
            "Engagement Metrics URL": analysis_links["engagement_metrics_url"],
            "Concise Summary URL": analysis_links["concise_summary_url"]
        })
    
    # Create DataFrame and save to CSV
    if not report_data:
        logger.warning("No recordings found for the report")
        return
        
    df = pd.DataFrame(report_data)
    report_path = os.path.join(temp_dir, "zoom_recordings_report.csv")
    df.to_csv(report_path, index=False)
    logger.info(f"Saved report to {report_path}")
    
    # Upload to Google Drive
    try:
        drive_service = get_drive_service()
        
        # Check if report already exists
        report_name = "Zoom Recordings Report"
        query = f"name = '{report_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{config.GOOGLE_DRIVE_ROOT_FOLDER}' in parents and trashed = false"
        results = drive_service.files().list(q=query).execute()
        
        if results.get('files'):
            # Update existing report
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
            # Create new report
            file_metadata = {
                'name': report_name,
                'parents': [config.GOOGLE_DRIVE_ROOT_FOLDER],
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            
            # Create media
            media = MediaFileUpload(
                report_path,
                mimetype='text/csv',
                resumable=True
            )
            
            # Upload file
            logger.info("Creating new report in Google Drive")
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            logger.info(f"Report created with ID: {file.get('id')}")
            logger.info(f"Report can be viewed at: {file.get('webViewLink')}")
        
    except Exception as e:
        logger.error(f"Error uploading report to Google Drive: {e}")
        logger.info(f"Report is still available locally at: {report_path}")
        
    return

async def main():
    """Main function to extract recordings and save to Drive."""
    parser = argparse.ArgumentParser(description="Extract historical recordings from Zoom")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--temp-dir", type=str, default="./temp", help="Temporary directory for downloads")
    parser.add_argument("--user-email", type=str, help="Specific user email to get recordings for")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="Set the logging level")
    
    args = parser.parse_args()
    
    # Set logging level based on command-line argument
    logger.setLevel(getattr(logging, args.log_level))
    
    # Set default dates if not provided
    if not args.start_date:
        args.start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not args.end_date:
        args.end_date = datetime.now().strftime("%Y-%m-%d")
        
    # Create temp directory
    os.makedirs(args.temp_dir, exist_ok=True)
    
    try:
        logger.info(f"Extracting recordings from {args.start_date} to {args.end_date}")
        if args.user_email:
            logger.info(f"Getting recordings only for user: {args.user_email}")
        
        # Get recordings
        zoom_client = ZoomClient()
        recordings = zoom_client.get_recordings(args.start_date, args.end_date, args.user_email)
        
        logger.info(f"Found {len(recordings)} recordings")
        
        # Process each recording
        for recording in recordings:
            topic = recording.get("topic", "Unknown Meeting")
            logger.info(f"Processing recording: {topic}")
            
            success = await process_recording(recording, args.temp_dir)
            if success:
                logger.info(f"Successfully processed recording: {topic}")
            else:
                logger.warning(f"Failed to process recording: {topic}")
                
        logger.info("Extraction completed")
        
        await create_summary_report(recordings, args.temp_dir)
        
    except Exception as e:
        logger.error(f"Error extracting recordings: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 