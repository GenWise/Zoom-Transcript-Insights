import pytest
import os
import tempfile
from typing import Dict, List

from app.models.schemas import TranscriptSegment, AnalysisRequest


@pytest.fixture
def sample_vtt_path():
    """Return the path to the sample VTT file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "data", "sample.vtt")


@pytest.fixture
def temp_vtt_file():
    """Create a temporary VTT file for testing."""
    temp_vtt = tempfile.NamedTemporaryFile(suffix=".vtt", delete=False)
    with open(temp_vtt.name, "w") as f:
        f.write("""WEBVTT

00:00:00.000 --> 00:00:05.000
John Smith: Hello everyone, welcome to the meeting.

00:00:06.000 --> 00:00:10.000
John Smith: Today we'll be discussing the course structure.

00:00:11.000 --> 00:00:15.000
Jane Doe: Thanks John, I have some questions about the syllabus.
""")
    
    yield temp_vtt.name
    
    # Clean up after the test
    os.unlink(temp_vtt.name)


@pytest.fixture
def sample_segments() -> List[TranscriptSegment]:
    """Create sample transcript segments for testing."""
    return [
        TranscriptSegment(
            start_time="00:00:00.000",
            end_time="00:00:05.000",
            speaker="John Smith",
            text="Hello everyone, welcome to the meeting."
        ),
        TranscriptSegment(
            start_time="00:00:06.000",
            end_time="00:00:10.000",
            speaker="John Smith",
            text="Today we'll be discussing the course structure."
        ),
        TranscriptSegment(
            start_time="00:00:11.000",
            end_time="00:00:15.000",
            speaker="Jane Doe",
            text="Thanks John, I have some questions about the syllabus."
        )
    ]


@pytest.fixture
def sample_analysis_request(temp_vtt_file) -> AnalysisRequest:
    """Create a sample analysis request for testing."""
    return AnalysisRequest(
        transcript_path=temp_vtt_file,
        analysis_types=["executive_summary", "pedagogical_analysis"]
    )


@pytest.fixture
def sample_school_mapping() -> Dict[str, str]:
    """Create a sample mapping of participants to schools."""
    return {
        "John Smith": "University A",
        "Jane Doe": "University B",
        "Student 1": "University C",
        "Student 2": "University D",
        "Instructor": "University X"
    }


@pytest.fixture
def webhook_secret():
    """Set a webhook secret for testing"""
    import config
    original_secret = config.ZOOM_WEBHOOK_SECRET
    config.ZOOM_WEBHOOK_SECRET = "test_webhook_secret"
    yield config.ZOOM_WEBHOOK_SECRET
    config.ZOOM_WEBHOOK_SECRET = original_secret 