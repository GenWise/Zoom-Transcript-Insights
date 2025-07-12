import requests
import logging
import time
import jwt
import os
import tempfile
from typing import Dict, Any, Optional

import config
from app.models.schemas import ZoomRecording

logger = logging.getLogger(__name__)

def generate_jwt_token() -> str:
    """
    Generate a JWT token for Zoom API authentication.
    """
    expiration = int(time.time()) + 3600  # Token valid for 1 hour
    
    payload = {
        "iss": config.ZOOM_CLIENT_ID,
        "exp": expiration
    }
    
    token = jwt.encode(
        payload,
        config.ZOOM_CLIENT_SECRET,
        algorithm="HS256"
    )
    
    return token

async def get_recording_info(meeting_uuid: str) -> ZoomRecording:
    """
    Get recording information from Zoom API.
    
    Args:
        meeting_uuid: UUID of the meeting
        
    Returns:
        ZoomRecording object with recording information
    """
    try:
        token = generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{config.ZOOM_BASE_URL}/meetings/{meeting_uuid}/recordings"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return ZoomRecording(**data)
    
    except Exception as e:
        logger.error(f"Error getting recording info: {e}")
        raise

async def download_transcript(download_url: str, file_path: str = None) -> bool:
    """
    Download a transcript file from Zoom.
    
    Args:
        download_url: URL to download the transcript
        file_path: Path to save the transcript file (optional)
        
    Returns:
        True if download was successful, False otherwise
    """
    try:
        token = generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        
        # If file_path is provided, save to that path
        if file_path:
            with open(file_path, 'wb') as f:
                f.write(response.content)
        # Otherwise save to temp file
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".vtt") as temp_file:
                temp_file.write(response.content)
                return temp_file.name
        
        return True
    
    except Exception as e:
        logger.error(f"Error downloading transcript: {e}")
        return False

async def list_recordings(from_date: str, to_date: Optional[str] = None) -> Dict[str, Any]:
    """
    List recordings for the account.
    
    Args:
        from_date: Start date in 'YYYY-MM-DD' format
        to_date: End date in 'YYYY-MM-DD' format (optional)
        
    Returns:
        Dictionary with recording information
    """
    try:
        token = generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "from": from_date,
            "to": to_date or from_date,
            "page_size": 100
        }
        
        url = f"{config.ZOOM_BASE_URL}/accounts/{config.ZOOM_ACCOUNT_ID}/recordings"
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    except Exception as e:
        logger.error(f"Error listing recordings: {e}")
        raise 