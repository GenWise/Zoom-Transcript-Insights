import pytest
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
import config

# Initialize TestClient with the app
client = TestClient(app)

# Sample webhook payload for testing
SAMPLE_WEBHOOK_PAYLOAD = {
    "event": "recording.completed",
    "payload": {
        "object": {
            "uuid": "test_meeting_uuid",
            "id": 12345,
            "host_id": "test_host_id",
            "topic": "Test Course - Session 1: Introduction",
            "type": 2,
            "start_time": "2023-01-01T10:00:00Z",
            "timezone": "UTC",
            "duration": 60,
            "total_size": 1000000,
            "recording_count": 3,
            "share_url": "https://zoom.us/rec/share/test-share-url",
            "recording_files": [
                {
                    "id": "test_file_id_1",
                    "meeting_id": "test_meeting_id",
                    "recording_start": "2023-01-01T10:00:00Z",
                    "recording_end": "2023-01-01T11:00:00Z",
                    "file_type": "TRANSCRIPT",
                    "file_size": 50000,
                    "play_url": "https://zoom.us/rec/play/test-play-url",
                    "download_url": "https://zoom.us/rec/download/test-download-url",
                    "status": "completed",
                    "recording_type": "shared_screen_with_speaker_view"
                }
            ]
        }
    },
    "event_ts": 1672567200000
}

def generate_signature(payload, timestamp, secret):
    """Generate a Zoom webhook signature for testing"""
    message = f"v0:{timestamp}:{payload}"
    hash_object = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    )
    return f"v0={hash_object.hexdigest()}"

@patch("app.api.webhook.get_recording_info")
@patch("app.api.webhook.download_transcript")
@patch("app.api.webhook.generate_analysis")
@patch("app.api.webhook.create_folder_structure")
@patch("app.api.webhook.upload_to_drive")
def test_recording_completed_webhook(
    mock_upload_to_drive, 
    mock_create_folder_structure,
    mock_generate_analysis, 
    mock_download_transcript, 
    mock_get_recording_info, 
    webhook_secret
):
    """Test the recording completed webhook endpoint"""
    # Setup mocks
    mock_get_recording_info.return_value = SAMPLE_WEBHOOK_PAYLOAD["payload"]["object"]
    mock_download_transcript.return_value = True
    mock_generate_analysis.return_value = MagicMock()
    mock_create_folder_structure.return_value = {"course_folder_id": "test_course_id", "session_folder_id": "test_session_id"}
    mock_upload_to_drive.return_value = {"transcript": "test_file_id"}
    
    # Prepare request
    payload = json.dumps(SAMPLE_WEBHOOK_PAYLOAD)
    timestamp = "1672567200000"
    signature = generate_signature(payload, timestamp, webhook_secret)
    
    # Make request
    response = client.post(
        "/webhook/recording-completed",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }
    )
    
    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["meeting_uuid"] == "test_meeting_uuid"
    
    # Verify mocks were called
    mock_get_recording_info.assert_called_once_with("test_meeting_uuid")
    mock_download_transcript.assert_called_once()
    mock_generate_analysis.assert_called_once()
    mock_create_folder_structure.assert_called_once()
    mock_upload_to_drive.assert_called_once()

def test_webhook_health():
    """Test the webhook health endpoint"""
    response = client.get("/webhook/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("app.api.webhook.get_recording_info")
def test_invalid_signature(mock_get_recording_info, webhook_secret):
    """Test that requests with invalid signatures are rejected"""
    # Prepare request with invalid signature
    payload = json.dumps(SAMPLE_WEBHOOK_PAYLOAD)
    timestamp = "1672567200000"
    invalid_signature = "v0=invalid_signature_hash"
    
    # Make request
    response = client.post(
        "/webhook/recording-completed",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-zm-signature": invalid_signature,
            "x-zm-request-timestamp": timestamp
        }
    )
    
    # Check response
    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]
    mock_get_recording_info.assert_not_called()

def test_missing_signature_headers(webhook_secret):
    """Test that requests without signature headers are rejected"""
    # Make request without headers
    response = client.post(
        "/webhook/recording-completed",
        json=SAMPLE_WEBHOOK_PAYLOAD
    )
    
    # Check response
    assert response.status_code == 401
    assert "Missing Zoom signature headers" in response.json()["detail"]

# Sample deauthorization payload for testing
SAMPLE_DEAUTH_PAYLOAD = {
    "event": "app.deauthorized",
    "payload": {
        "account_id": "test_account_id",
        "user_id": "test_user_id",
        "signature": "test_signature",
        "deauthorization_time": "2023-01-01T12:00:00Z"
    },
    "event_ts": 1672574400000
}

def test_deauthorization_webhook(webhook_secret):
    """Test the app deauthorization webhook endpoint"""
    # Prepare request
    payload = json.dumps(SAMPLE_DEAUTH_PAYLOAD)
    timestamp = "1672574400000"
    signature = generate_signature(payload, timestamp, webhook_secret)
    
    # Make request
    response = client.post(
        "/webhook/deauthorization",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }
    )
    
    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["account_id"] == "test_account_id"

# Sample meeting deleted payload for testing
SAMPLE_MEETING_DELETED_PAYLOAD = {
    "event": "meeting.deleted",
    "payload": {
        "object": {
            "id": "test_meeting_id",
            "uuid": "test_meeting_uuid",
            "host_id": "test_host_id",
            "topic": "Test Meeting",
            "type": 2,
            "start_time": "2023-01-01T14:00:00Z",
            "timezone": "UTC",
            "duration": 60
        }
    },
    "event_ts": 1672581600000
}

def test_meeting_deleted_webhook(webhook_secret):
    """Test the meeting deleted webhook endpoint"""
    # Prepare request
    payload = json.dumps(SAMPLE_MEETING_DELETED_PAYLOAD)
    timestamp = "1672581600000"
    signature = generate_signature(payload, timestamp, webhook_secret)
    
    # Make request
    response = client.post(
        "/webhook/meeting-deleted",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-zm-signature": signature,
            "x-zm-request-timestamp": timestamp
        }
    )
    
    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["meeting_id"] == "test_meeting_id"
    assert response.json()["meeting_uuid"] == "test_meeting_uuid" 