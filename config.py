import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Zoom API Configuration
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_WEBHOOK_SECRET = os.getenv("ZOOM_WEBHOOK_SECRET")
ZOOM_BASE_URL = "https://api.zoom.us/v2"

# Google Drive Configuration
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "sheets-and-python-340711-0c9221224a70.json")
GOOGLE_DRIVE_ROOT_FOLDER = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER", "1VPzWqLYUt3N1HRJkgjIAqRJCEMWmid32")

# Claude API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"

# FastAPI Settings
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Folder Structure Templates
FOLDER_STRUCTURE = {
    "course_folder": "{course_name}",
    "session_folder": "{session_name}_{date}",
    "files": {
        "transcript": "transcript.vtt",
        "chat_log": "chat_log.txt",
        "analysis": "analysis.json",
        "executive_summary": "executive_summary.md",
        "pedagogical_analysis": "pedagogical_analysis.md",
        "aha_moments": "aha_moments.md",
        "engagement_metrics": "engagement_metrics.json",
        "course_summary": "course_summary.md"
    }
}

# Claude Prompt Templates
CLAUDE_PROMPTS = {
    "executive_summary": """
You're analyzing a Zoom transcript from an educational session. 
Create a concise 6-10 line executive summary highlighting:
1. Main topics covered
2. Key teaching approaches used
3. Overall participant engagement
4. Notable outcomes or decisions
5. Areas of potential follow-up

Format this summary for school administrators who need a quick overview.

Transcript:
{transcript}
""",
    
    "pedagogical_analysis": """
Analyze this educational session transcript from a teaching and learning perspective.
In approximately 1.5 pages:
1. Identify the teaching strategies and methodologies employed
2. Evaluate the effectiveness of content delivery and knowledge building
3. Assess the scaffolding of concepts and learning progression
4. Note examples of effective questioning and discussion facilitation
5. Suggest potential improvements or alternative approaches

This analysis will be used by curriculum developers and instructional coaches.

Transcript:
{transcript}
""",
    
    "aha_moments": """
Identify 3-5 "AHA moments" in this educational session transcript.
For each moment:
1. Quote the relevant exchange
2. Explain why this represents a breakthrough in understanding
3. Note the teaching technique that facilitated this insight
4. Suggest how similar moments could be cultivated in future sessions

Transcript:
{transcript}
""",
    
    "engagement_analysis": """
Analyze participant engagement in this educational session.
For each participant:
1. Calculate total speaking time and frequency
2. Assess the quality and depth of contributions
3. Note patterns of interaction (questions, responses, initiating discussions)
4. Identify any participation changes throughout the session

Additionally, provide school-level engagement metrics by aggregating participants from the same institutions using this mapping:
{school_mapping}

Transcript:
{transcript}
"""
}
