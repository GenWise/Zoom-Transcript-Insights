# Recent Changes and Improvements

## Fixed Issues

### 1. Missing URLs in Zoom Report
- Fixed missing concise summary URLs in the Zoom Report
- Added automatic generation of concise summaries when executive summaries are created
- Ensured Drive Video URLs are properly captured and included in the report
- Created a dedicated script to update insight URLs in the report for all sessions

### 2. API Cost Optimization
- Added checks to avoid regenerating insights when files already exist
- Modified `process_drive_recordings.py` to only generate missing analyses
- Implemented smart detection of existing insight files before making API calls

### 3. Multiple Copies of Insights
- The system now properly identifies which insight files are referenced in the Zoom Report
- Files are consistently named and stored in the correct folder structure
- The Zoom Report now links to the correct, most recent versions of insights

### 4. Host Information in Zoom Report
- Fixed "Unknown" Host Name and Email issues in the Zoom Report
- Added a new method to fetch detailed user information from Zoom API
- Implemented fallback mechanisms when host information is incomplete

### 5. Meeting Password Access
- Added Meeting Password column to the Zoom Report
- Passwords are now extracted from the Zoom API response and saved in the report
- This allows users to easily access password-protected Zoom recordings

## New Features

### 1. GitHub Integration
- Added `setup_github.sh` script to initialize and push to GitHub
- Created appropriate .gitignore file for Python projects
- Simplified the process of publishing the codebase to GitHub

### 2. Improved Documentation
- Updated README.md with new features and capabilities
- Added detailed usage instructions for all scripts
- Expanded project structure documentation

### 3. Concise Summary Generation
- Improved the concise summary generation process
- Made it work better when called from other scripts
- Ensured concise summaries are generated and linked in the Zoom Report 

# Changes Log

## 2025-07-12: Insight URL Update System

We've implemented a robust system to ensure all insight URLs are properly updated in the Zoom Report:

### Insight URL Update Script
- Created `update_insight_urls.py` to find and update all insight URLs in the Zoom Report
- Implemented multiple matching strategies to find the correct session in the report:
  - Exact session name matching
  - Date-based matching
  - Partial name matching
  - UUID matching from metadata or transcript files
- Successfully updated 25 sessions with 125 insight URLs in the report

### Verification System
- Created `verify_report_updates.py` to confirm all sessions with insights have URLs in the report
- Added detailed logging of the update process
- Implemented checks to ensure all expected URL types are present for each session

### Drive Manager Improvements
- Enhanced the DriveManager class with better file listing and search capabilities
- Added support for shared drives and proper permission handling
- Improved error handling and retry logic for Drive API calls

### Other Improvements
- Added scripts to check for sessions with missing insights
- Implemented better logging throughout the system
- Created utility functions for common Drive and Sheets operations

These changes ensure that all generated insights are properly linked in the Zoom Report, making them easily accessible to users.

## 2025-07-12: Large Transcript Processing Improvements

We've made several improvements to handle large transcripts better and avoid Claude API rate limiting issues:

### API Queue System Enhancements
- Reduced default token limit from 40,000 to 30,000 tokens per minute (more conservative)
- Added chunking mechanism to break large requests into smaller pieces
- Implemented intelligent text splitting that preserves context
- Added dynamic delays between chunk processing based on size

### Analysis Processing Improvements
- Modified analysis service to process insight types sequentially instead of in parallel
- Added delays between different analysis types to avoid rate limits
- Improved error handling and retry logic for rate limiting errors
- Added better JSON parsing for engagement metrics

### Report Update Functionality
- Created dedicated function to update the report with insight URLs
- Implemented direct Sheets API updates for insight URLs
- Fixed sheet name handling to use the actual sheet name instead of hardcoding

### New Processing Scripts
1. **Retry Failed Processing Script** (`scripts/retry_failed_processing.py`)
   - Finds sessions marked as failed
   - Retries with increased backoff times
   - Updates report with insight URLs when successful

2. **Batch Processing Script** (`scripts/process_batch.py`)
   - Processes transcripts in smaller batches
   - Adds configurable delays between batches
   - Provides detailed success/failure statistics

### Other Improvements
- Increased initial backoff time from 60s to 120s for rate limit retries
- Added exponential backoff with doubling wait times between retries
- Improved logging with more detailed information
- Added better error handling throughout the system

These changes should significantly improve the system's ability to handle large transcripts and avoid rate limiting issues with the Claude API. 