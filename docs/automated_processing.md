# Automated Daily Processing

This document explains the automated daily processing system for Zoom recordings, insights generation, and report updates.

## Overview

The system includes a daily processing script that:

1. Extracts new recordings from Zoom
2. Processes recordings in Google Drive to generate insights
3. Updates the Zoom report with insight URLs
4. Sends email notifications with processing results

This script is designed to be run daily via cron to ensure that all new recordings are processed automatically.

## Setup

To set up the automated daily processing:

1. Make sure your `.env` file is properly configured with all required credentials
2. Run the setup script:

```bash
./scripts/setup_daily_processing.sh
```

This script will:
- Create a cron job to run the daily processing at 3:00 AM
- Add email notification settings to your `.env` file if not already present
- Make sure the necessary scripts are executable

## Email Notifications

The system can send email notifications with the results of the daily processing. To enable this feature, add the following settings to your `.env` file:

```
# Email notification settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
RECIPIENT_EMAIL=recipient@example.com
```

Notes:
- For Gmail, you'll need to create an App Password instead of using your regular password
- You can set multiple recipient emails by separating them with commas

## Manual Execution

You can manually run the daily processing script at any time:

```bash
cd /path/to/project
source .env
python scripts/daily_processing.py
```

## Logs

Logs for the daily processing are stored in the `logs` directory:

- `logs/daily_processing_YYYY-MM-DD.log`: Detailed logs for each daily run (preserved by date)
- `logs/cron_daily_processing.log`: Output from the cron job execution (overwritten daily)

The system automatically performs log rotation, keeping only the last 30 days of daily processing logs to prevent disk space issues.

## Components

The automated system consists of the following components:

### 1. Daily Processing Script (`scripts/daily_processing.py`)

This is the main script that orchestrates the entire workflow:
- Extracts recordings from the previous day
- Processes recordings to generate insights
- Updates the Zoom report with insight URLs
- Sends email notifications

### 2. Extract Historical Recordings (`scripts/extract_historical_recordings.py`)

This script:
- Connects to the Zoom API
- Downloads recordings from the specified date range
- Creates folders in Google Drive
- Updates the Zoom report with recording details

### 3. Process Drive Recordings (`scripts/process_drive_recordings.py`)

This script:
- Scans Google Drive for recordings
- Generates insights using Claude API
- Uploads insights to Google Drive

### 4. Update Insight URLs (`update_insight_urls.py`)

This script:
- Finds all sessions with insights in Google Drive
- Updates the Zoom report with URLs to the insight files

## Troubleshooting

If you encounter issues with the automated processing:

1. Check the logs in the `logs` directory
2. Verify that your `.env` file has all required credentials
3. Make sure the cron job is properly set up:
   ```bash
   crontab -l | grep daily_processing
   ```
4. Try running the script manually to see if there are any errors
5. Check if there are any rate limiting issues with the APIs

## Customization

You can customize the daily processing by editing the `scripts/daily_processing.py` file:

- Change the processing time by modifying the cron schedule in `setup_daily_processing.sh`
- Adjust the backoff time for API rate limiting
- Add additional processing steps or checks
- Customize the email notification format 