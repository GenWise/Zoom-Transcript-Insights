#!/bin/bash
# Environment variables for Zoom Transcript Insights
# Copy this file to .env and update with your credentials
# Usage: source .env

# =============================================
# Zoom API Credentials
# =============================================
# Create an OAuth app in the Zoom Marketplace:
# https://marketplace.zoom.us/develop/create

# Client ID from your Zoom OAuth app
export ZOOM_CLIENT_ID="your_zoom_client_id"

# Client Secret from your Zoom OAuth app
export ZOOM_CLIENT_SECRET="your_zoom_client_secret"

# Your Zoom Account ID (found in Account Profile)
export ZOOM_ACCOUNT_ID="your_zoom_account_id"

# Base URL for Zoom API (usually no need to change)
export ZOOM_BASE_URL="https://api.zoom.us/v2"

# Webhook secret (only needed if using webhooks)
export ZOOM_WEBHOOK_SECRET="your_zoom_webhook_secret"

# =============================================
# Google Drive API Credentials
# =============================================
# Create a service account and download JSON credentials:
# https://console.cloud.google.com/

# Path to your Google service account JSON file
export GOOGLE_CREDENTIALS_FILE="path_to_your_credentials.json"

# ID of the root folder in Google Drive
# This is the part of the URL after "folders/" when viewing the folder
export GOOGLE_DRIVE_ROOT_FOLDER="your_root_folder_id"

# =============================================
# Claude API Credentials
# =============================================
# Get an API key from Anthropic:
# https://www.anthropic.com/

# Your Claude API key
export CLAUDE_API_KEY="your_claude_api_key"

# Claude model to use (default: claude-3-7-sonnet-20250219)
export CLAUDE_MODEL="claude-3-7-sonnet-20250219"

# =============================================
# Email Notification Settings (Optional)
# =============================================
# Only needed if using email notifications

# SMTP server settings
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"

# Sender and recipient settings
export EMAIL_FROM="your_email@gmail.com"
export EMAIL_SUBJECT_PREFIX="[Zoom Insights]"

# =============================================
# Application Settings
# =============================================

# Host and port for the web interface
export APP_HOST="0.0.0.0"
export APP_PORT="8000"

# Debug mode (set to "True" or "False")
export DEBUG="True"

# Folder structure configuration
# These settings define how files are organized in Google Drive
export FOLDER_STRUCTURE='{
    "folders": {
        "course": "{course_name}",
        "session": "{session_name}_{session_date}"
    },
    "files": {
        "transcript": "transcript.vtt",
        "chat_log": "chat_log.txt",
        "metadata": "meeting_metadata.json",
        "executive_summary": "executive_summary.md",
        "pedagogical_analysis": "pedagogical_analysis.md",
        "aha_moments": "aha_moments.md",
        "engagement_metrics": "engagement_metrics.json",
        "concise_summary": "concise_summary.md"
    }
}'

echo "Environment variables loaded successfully!"
