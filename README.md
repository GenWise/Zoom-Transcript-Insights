# Zoom Transcript Insights

An automated system to extract insights from Zoom recording transcripts for online educational courses.

## Overview

This application processes Zoom meeting transcripts (VTT files) and uses Claude 3.7 Sonnet to generate various types of insights:

1. **Executive Summary**: 6-10 line summary of key topics and outcomes
2. **Concise Summary**: Ultra-short summary for school administrators
3. **Pedagogical Analysis**: 1.5 page analysis of teaching strategies and effectiveness
4. **AHA Moments**: Identification of breakthrough moments in understanding
5. **Engagement Metrics**: Analysis of participant engagement and speaking patterns

## Features

- Upload and process VTT transcripts manually
- Receive Zoom webhook notifications for automated processing
- Store analysis results in Google Drive with organized folder structure
- Simple web interface for uploading transcripts and viewing results

## Setup Instructions

### Prerequisites

- Python 3.9+
- Zoom API credentials
- Google Drive API credentials
- Claude API key

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd zoom-transcript-insights
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Copy `env_template.sh` to a new file called `.env`:
     ```
     cp env_template.sh .env
     ```
   - Edit the `.env` file with your specific credentials
   - Source the environment file:
     ```
     source .env
     ```

4. Configure API credentials:

   #### Zoom API Setup
   - Create a Zoom OAuth app in the [Zoom Marketplace](https://marketplace.zoom.us/)
   - Add the required scopes:
     - `recording:read:admin`
     - `recording:write:admin`
     - `cloud_recording:read:list_user_recordings:admin`
     - `user:read:admin`
   - Get your Client ID, Client Secret, and Account ID
   - Update these values in your `.env` file

   #### Google Drive Setup
   - Create a project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Drive API
   - Create a service account and download the JSON credentials file
   - Place the JSON file in your project directory
   - **IMPORTANT**: Service accounts don't have their own storage quota. To avoid storage errors:
     - Create a shared drive in Google Drive (requires Google Workspace)
     - Share it with your service account email (as Content Manager)
     - Get the shared drive ID from the URL and add it to `GOOGLE_SHARED_DRIVE_ID` in your `.env` file
     - See `docs/shared_drive_setup.md` for detailed instructions
   - Create a folder in Google Drive and share it with the service account email
   - Get the folder ID from the URL and update `GOOGLE_DRIVE_ROOT_FOLDER` in your `.env` file
   - Update `GOOGLE_CREDENTIALS_FILE` to point to your JSON file

   #### Claude API Setup
   - Get an API key from [Anthropic](https://www.anthropic.com/)
   - Update `CLAUDE_API_KEY` in your `.env` file

5. Create necessary directories:
   ```
   mkdir -p app/static temp logs
   ```

### Using With Different Accounts

To use this codebase with different Zoom accounts or Google Drive setups:

1. **For different Zoom accounts**:
   - Create a new OAuth app in the Zoom Marketplace for each account
   - Update the `.env` file with the new credentials
   - Source the updated environment file before running scripts

2. **For different Google Drive accounts**:
   - Create a new service account for each Google account
   - Download the new credentials JSON file
   - Update the `.env` file to point to the new JSON file
   - Create and share a folder with the new service account
   - Update the `GOOGLE_DRIVE_ROOT_FOLDER` value

3. **Quick switch between configurations**:
   - Create multiple environment files (e.g., `.env.user1`, `.env.user2`)
   - Source the appropriate file before running scripts:
     ```
     source .env.user1  # For user 1
     # or
     source .env.user2  # For user 2
     ```

### Google Drive Setup

1. Create a project in Google Cloud Console
2. Enable the Google Drive API
3. Create a service account and download the credentials JSON file
4. Create a root folder in Google Drive and share it with the service account email
5. Get the folder ID from the URL and add it to your `.env` file

### Zoom API Setup

1. Create a Zoom App in the Zoom Marketplace (OAuth app type)
2. Add the required scopes:
   - `recording:read:admin`
   - `recording:write:admin`
3. Configure the redirect URL to your application's domain
4. Get the Client ID and Client Secret and add them to your `.env` file

### Webhook Setup (Optional)

1. In your Zoom App settings, add a webhook endpoint
2. Set the endpoint URL to `https://your-domain.com/webhook/recording-completed`
3. Subscribe to the `recording.completed` event
4. Get the webhook verification token and add it to your `.env` file as `ZOOM_WEBHOOK_SECRET`

## Usage

### Running the Application

```
python main.py
```

The application will be available at http://localhost:8000 (or the port you configured).

### Manual Upload

1. Visit the web interface at http://localhost:8000
2. Fill out the form with course and session information
3. Upload a VTT transcript file
4. Select the types of analysis you want to generate
5. Click "Generate Insights"

## Script Usage Guide

### 1. Processing Historical Recordings

To extract and process historical recordings from your Zoom account:

```bash
python scripts/extract_historical_recordings.py --start-date 2023-01-01 --end-date 2023-12-31 --temp-dir ./temp
```

**Parameters:**
- `--start-date`: Beginning date for recording search (YYYY-MM-DD format)
- `--end-date`: End date for recording search (YYYY-MM-DD format)
- `--user-email`: (Optional) Specific user's recordings to extract
- `--temp-dir`: Directory for temporary files (default: ./temp)
- `--log-level`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**What this script does:**
1. Authenticates with Zoom API using your credentials
2. Downloads transcripts and metadata from your Zoom account
3. Creates an organized folder structure in Google Drive
4. Generates insights using Claude API (if transcripts are available)
5. Creates a comprehensive report (CSV and Google Sheet) with:
   - Meeting details (title, host, date, duration)
   - Meeting passwords for accessing recordings
   - Links to all recordings, transcripts, and generated insights

### 2. Processing Existing Drive Files

If you already have transcripts in Google Drive but need to generate insights:

```bash
python scripts/process_drive_recordings.py --log-level INFO --retry-failed
```

**Parameters:**
- `--temp-dir`: Directory for temporary files (default: ./temp)
- `--course`: (Optional) Process only a specific course
- `--log-level`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--retry-failed`: Retry previously failed folders
- `--backoff-time`: Time to wait after rate limit errors (seconds)

**What this script does:**
1. Connects to Google Drive using your credentials
2. Finds all course folders and session folders with transcripts
3. Checks which insights are missing for each session
4. Generates only the missing insights (saving API costs)
5. Marks folders as processed to avoid redundant processing

### 3. Generating Missing Concise Summaries

To specifically generate concise summaries from existing executive summaries:

```bash
python generate_missing_concise_summaries.py --batch-size 3 --delay 90
```

**Parameters:**
- `--temp-dir`: Directory for temporary files (default: ./temp)
- `--log-level`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--batch-size`: Number of summaries to process in parallel
- `--delay`: Seconds to wait between batches (to avoid API rate limits)

**What this script does:**
1. Finds all executive summaries in Google Drive
2. Checks which ones don't have corresponding concise summaries
3. Downloads executive summaries and generates concise versions
4. Uploads concise summaries to the same folders
5. Updates the Zoom report with links to the concise summaries

### 4. Extracting Meeting Passwords

To extract meeting passwords and update the Zoom report:

```bash
python extract_meeting_passwords.py
```

**Parameters:**
- `--temp-dir`: Directory for temporary files (default: ./temp)
- `--log-level`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**What this script does:**
1. Reads the existing Zoom recordings report
2. For each recording without a password, fetches details from Zoom API
3. Extracts the meeting password and host information
4. Updates the report with the new information

### 5. Updating Insight URLs in the Zoom Report

To update the Zoom report with URLs to all insight files:

```bash
python update_insight_urls.py
```

**Parameters:**
- `--log-level`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**What this script does:**
1. Connects to Google Drive using your credentials
2. Finds all session folders with generated insights
3. Uses multiple matching strategies to find the corresponding report entries:
   - Exact session name matching
   - Date-based matching
   - Partial name matching
   - UUID matching from metadata or transcript files
4. Updates the report with URLs to all insight files (executive summaries, pedagogical analyses, etc.)

For more details, see [docs/insight_url_update.md](docs/insight_url_update.md).

### 6. Verifying Report Updates

To verify that all sessions with insights have URLs in the Zoom report:

```bash
python verify_report_updates.py
```

**What this script does:**
1. Finds all sessions with insights in Google Drive
2. Checks which sessions in the report have URLs
3. Verifies that all sessions with insights have URLs in the report
4. Checks if all URL types are present for each session
5. Provides a summary of the update status

### Webhook Integration

When configured correctly, the application will automatically process new recordings when they become available in your Zoom account.

## Testing

The application includes a comprehensive test suite. For details, see [TESTING.md](TESTING.md).

### Running Tests

```bash
# Run all tests
./run_tests.sh

# Run tests with coverage reporting
./run_tests_with_coverage.sh
```

## Project Structure

```
Insights_from_Online_Courses/
├── app/
│   ├── api/
│   │   ├── routes.py
│   │   └── webhook.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── analysis.py
│   │   ├── drive_manager.py
│   │   ├── vtt_parser.py
│   │   └── zoom_client.py
│   ├── static/
│   └── templates/
│       └── index.html
├── config.py
├── insights/
│   ├── aha_moments.md
│   ├── concise_summary.md
│   ├── engagement_summary.md
│   ├── executive_summary.md
│   ├── pedagogical_analysis.md
│   └── visualizations/
├── main.py
├── scripts/
│   ├── extract_historical_recordings.py
│   ├── process_drive_recordings.py
│   └── README.md
├── requirements.txt
├── setup_github.sh
└── README.md
```

## GitHub Setup

To initialize the Git repository and push to GitHub:

```bash
./setup_github.sh https://github.com/yourusername/your-repo-name.git
```

This script will:
1. Initialize a Git repository if needed
2. Create an appropriate .gitignore file
3. Add and commit all files
4. Push to the specified GitHub repository

## License

[MIT License](LICENSE) 