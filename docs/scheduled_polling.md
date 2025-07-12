# Scheduled Polling for Zoom Recordings

This document explains how scheduled polling is used to extract Zoom recordings instead of using webhooks.

## Overview

Instead of relying on webhooks that require a publicly accessible endpoint (like Vercel), we use a scheduled approach that periodically checks for new recordings using the Zoom API. This approach is simpler to set up and doesn't require maintaining a public server.

## How It Works

1. A cron job runs every day at 8pm IST
2. The job executes the `extract_historical_recordings.py` script
3. The script fetches recordings created in the past 24 hours
4. Transcripts are downloaded and analysis is generated
5. Results are uploaded to Google Drive
6. The Zoom report CSV is updated

## Setup

The scheduled polling is set up using the `setup_scheduled_polling.sh` script:

```bash
# Run the setup script
./scripts/setup_scheduled_polling.sh
```

This script:
- Creates a cron job that runs at 8pm IST every day
- Sets up logging for the scheduled job
- Creates a script for manual extraction when needed

## Manual Extraction

If you need to extract recordings outside the scheduled time, you can use the provided manual extraction script:

```bash
# Extract recordings from yesterday to today
./scripts/run_manual_extraction.sh

# Extract recordings from a specific date range
./scripts/run_manual_extraction.sh --start-date 2023-01-01 --end-date 2023-01-31
```

## Logs

Logs from the scheduled extraction are saved in the `logs` directory with filenames like:
```
scheduled_extraction_YYYYMMDD.log
```

## Advantages Over Webhooks

1. **Simplicity**: No need to set up and maintain a public server
2. **Security**: No public endpoints exposed
3. **Reliability**: Not dependent on external services like Vercel
4. **Control**: Easy to adjust the schedule or run manual extractions

## Limitations

1. **Latency**: Recordings are processed on a schedule, not immediately
2. **API Usage**: Regular polling may increase API usage
3. **Missed Events**: Events like meeting deletions won't trigger immediate actions

## Future Improvements

In the future, we could:
1. Implement multiple schedules (e.g., morning and evening)
2. Add error recovery mechanisms
3. Implement a notification system for failed extractions
4. Add a simple web interface to view extraction status 