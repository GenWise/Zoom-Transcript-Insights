# Zoom Transcript Insights - Requirements & Design

## Project Overview
An automated system to extract insights from Zoom recording transcripts for online educational courses, with a compressed timeline of 2 days for implementation.

## Detailed Requirements

### 1. Data Sources
- **Zoom Transcripts (VTT files)**: Primary source containing speaker names, timestamps, and dialogue
- **Zoom Chat Logs**: Secondary source for Q&A sessions and participant engagement
- **Participant List**: Spreadsheet with participant names and affiliated schools

### 2. Insight Types
- **Executive Summary (6-10 lines)**: Key topics, outcomes, and decisions for school administrators
- **Pedagogical Analysis (1.5 pages max)**: Teaching strategies, content effectiveness, learning progression
- **AHA Moments**: Breakthrough moments of understanding or insight during sessions
- **Engagement Metrics**: Speaking time, interaction frequency, and quality of participation

### 3. Analysis Levels
- **Session Level**: Individual session insights
- **Course Level**: Aggregated insights across multiple sessions
- **Product Level**: High-level insights across multiple courses

### 4. System Components
- **Zoom API Integration**: Webhook notifications and transcript retrieval
- **Google Drive Organization**: Structured storage of files and analyses
- **Claude 3.7 Sonnet Integration**: AI-powered insight generation
- **Processing Pipeline**: VTT parsing and multi-level analysis
- **Simple Web Interface**: Browse, search, and request insights

## API Access Requirements

### Zoom API
- **Authentication**: OAuth 2.0
- **Required Endpoints**:
  - `GET /recordings`: Retrieve recording metadata
  - `GET /recording/{meetingId}/transcript`: Retrieve VTT transcripts
  - `POST /webhooks`: Register webhook for recording completion notifications

### Google Drive API
- **Authentication**: OAuth 2.0 or Service Account
- **Required Endpoints**:
  - `files.create`: Upload files to Google Drive
  - `files.get`: Retrieve file metadata
  - `files.list`: List files in a directory
  - `folders.create`: Create folder hierarchy

### Claude API
- **Authentication**: API Key
- **Endpoints**:
  - Messages API for sending prompts and receiving completions

## Folder Structure
```
Courses/
├── [Course Name]/
│   ├── Session_1_[Name]_[Date]/ 
│   │   ├── transcript.vtt
│   │   ├── chat_log.txt
│   │   ├── analysis.json
│   │   ├── executive_summary.md
│   │   ├── pedagogical_analysis.md
│   │   ├── aha_moments.md
│   │   └── engagement_metrics.json
│   ├── Session_2_[Name]_[Date]/
│   └── course_summary.md
```

## Claude Prompt Design

### Executive Summary Prompt
```
You're analyzing a Zoom transcript from an educational session. 
Create a concise 6-10 line executive summary highlighting:
1. Main topics covered
2. Key teaching approaches used
3. Overall participant engagement
4. Notable outcomes or decisions
5. Areas of potential follow-up

Format this summary for school administrators who need a quick overview.
```

### Pedagogical Analysis Prompt
```
Analyze this educational session transcript from a teaching and learning perspective.
In approximately 1.5 pages:
1. Identify the teaching strategies and methodologies employed
2. Evaluate the effectiveness of content delivery and knowledge building
3. Assess the scaffolding of concepts and learning progression
4. Note examples of effective questioning and discussion facilitation
5. Suggest potential improvements or alternative approaches

This analysis will be used by curriculum developers and instructional coaches.
```

### AHA Moments Prompt
```
Identify 3-5 "AHA moments" in this educational session transcript.
For each moment:
1. Quote the relevant exchange
2. Explain why this represents a breakthrough in understanding
3. Note the teaching technique that facilitated this insight
4. Suggest how similar moments could be cultivated in future sessions
```

### Engagement Analysis Prompt
```
Analyze participant engagement in this educational session.
For each participant:
1. Calculate total speaking time and frequency
2. Assess the quality and depth of contributions
3. Note patterns of interaction (questions, responses, initiating discussions)
4. Identify any participation changes throughout the session

Additionally, provide school-level engagement metrics by aggregating participants from the same institutions.
```

## Technical Dependencies
- Python 3.9+
- FastAPI or Flask
- Google API Python Client
- Zoom API Python Client
- Anthropic Python Client
- VTT parsing library (webvtt-py)
- Frontend: Simple HTML/CSS/JS or Streamlit

## Compressed Timeline (2 Days)
### Day 1
- Morning: Set up API connections (Zoom, Google Drive, Claude)
- Afternoon: Develop core transcript processing and analysis pipeline

### Day 2
- Morning: Implement basic web interface and testing
- Afternoon: Process historical recordings and refine system
