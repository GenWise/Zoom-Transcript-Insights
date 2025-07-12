# Insight URL Update Process

This document explains how to update the Zoom Report with insight URLs for all sessions.

## Overview

The system includes scripts to automatically update the Zoom Report with URLs to insight files (executive summaries, pedagogical analyses, etc.) stored in Google Drive. These scripts ensure that all sessions with generated insights have their URLs properly linked in the report.

## Prerequisites

1. Ensure you have the `.env` file with the following variables:
   - `ZOOM_REPORT_ID`: The ID of the Google Sheets report to update
   - `GOOGLE_CREDENTIALS_FILE`: Path to the Google service account credentials file
   - `GOOGLE_DRIVE_ROOT_FOLDER`: ID of the root folder in Google Drive
   - `USE_SHARED_DRIVE`: Set to "true" if using a shared drive
   - `GOOGLE_SHARED_DRIVE_ID`: ID of the shared drive (if applicable)

2. Make sure the Google service account has:
   - Read access to all course folders and session folders
   - Write access to the Zoom Report spreadsheet

## Available Scripts

### 1. Update Insight URLs

The `update_insight_urls.py` script finds all sessions with insights and updates their URLs in the Zoom Report.

```bash
./update_insight_urls.py
```

This script:
- Connects to Google Drive
- Finds all session folders with generated insights
- Extracts meeting UUID from metadata or transcript
- Matches with the report by UUID or session name
- Updates the report with insight URLs

#### Matching Strategy

The script uses multiple strategies to match sessions with report entries:
1. Exact match by session name
2. Date-based matching (extracts date from session name)
3. Partial matching (session name contained in topic or vice versa)
4. UUID matching from metadata or transcript files

### 2. Verify Report Updates

The `verify_report_updates.py` script checks if all sessions with insights have URLs in the Zoom Report.

```bash
./verify_report_updates.py
```

This script:
- Finds all sessions with insights
- Checks which sessions in the report have URLs
- Verifies that all sessions with insights have URLs in the report
- Checks if all URL types are present for each session

## Troubleshooting

If some sessions are not being updated, check the following:

1. **Session Naming**: Ensure session folder names follow the standard format (e.g., `Course_YYYY-MM-DD`)
2. **Meeting Topics**: Check if the meeting topics in the Zoom Report match the session names
3. **UUID Matching**: Verify that meeting metadata or transcript files contain the UUID
4. **File Names**: Ensure insight files use the standard names:
   - `executive_summary.md`
   - `pedagogical_analysis.md`
   - `aha_moments.md`
   - `engagement_metrics.json`
   - `concise_summary.md`

## Manual Updates

If automatic matching fails for some sessions, you can manually update the report:

1. Find the session folder in Google Drive
2. Open each insight file and copy its URL
3. Paste the URL in the corresponding column in the Zoom Report 