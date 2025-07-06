import unittest
import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.schemas import AnalysisRequest, TranscriptSegment
from app.services.analysis import (
    generate_analysis,
    format_transcript_for_claude,
    call_claude,
    generate_executive_summary,
    generate_pedagogical_analysis,
    generate_aha_moments,
    generate_engagement_analysis,
    calculate_speaker_stats
)

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary VTT file for testing
        self.temp_vtt = tempfile.NamedTemporaryFile(suffix=".vtt", delete=False)
        with open(self.temp_vtt.name, "w") as f:
            f.write("""WEBVTT

00:00:00.000 --> 00:00:05.000
John Smith: Hello everyone, welcome to the meeting.

00:00:06.000 --> 00:00:10.000
John Smith: Today we'll be discussing the course structure.

00:00:11.000 --> 00:00:15.000
Jane Doe: Thanks John, I have some questions about the syllabus.
""")
        
        # Create sample segments for testing
        self.sample_segments = [
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
        
        # Sample analysis request
        self.sample_request = AnalysisRequest(
            transcript_path=self.temp_vtt.name,
            analysis_types=["executive_summary", "pedagogical_analysis"]
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_vtt.name)
    
    def test_format_transcript_for_claude(self):
        """Test formatting transcript segments for Claude."""
        formatted = format_transcript_for_claude(self.sample_segments)
        
        # Check the format
        expected = (
            "[00:00:00.000 - 00:00:05.000] John Smith: Hello everyone, welcome to the meeting.\n\n"
            "[00:00:06.000 - 00:00:10.000] John Smith: Today we'll be discussing the course structure.\n\n"
            "[00:00:11.000 - 00:00:15.000] Jane Doe: Thanks John, I have some questions about the syllabus."
        )
        
        self.assertEqual(formatted, expected)
    
    def test_calculate_speaker_stats(self):
        """Test calculating speaker statistics."""
        stats = calculate_speaker_stats(self.sample_segments)
        
        # Check that we have stats for both speakers
        self.assertIn("John Smith", stats)
        self.assertIn("Jane Doe", stats)
        
        # Check John Smith's stats
        self.assertEqual(stats["John Smith"]["total_segments"], 2)
        self.assertEqual(stats["John Smith"]["total_words"], 13)
        self.assertAlmostEqual(stats["John Smith"]["total_duration_seconds"], 9.0)


# Pytest-style async tests to properly handle coroutines
@pytest.mark.asyncio
class TestAnalysisAsync:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # Setup
        self.temp_vtt = tempfile.NamedTemporaryFile(suffix=".vtt", delete=False)
        with open(self.temp_vtt.name, "w") as f:
            f.write("""WEBVTT

00:00:00.000 --> 00:00:05.000
John Smith: Hello everyone, welcome to the meeting.

00:00:06.000 --> 00:00:10.000
John Smith: Today we'll be discussing the course structure.

00:00:11.000 --> 00:00:15.000
Jane Doe: Thanks John, I have some questions about the syllabus.
""")
        
        # Create sample segments for testing
        self.sample_segments = [
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
        
        # Sample analysis request
        self.sample_request = AnalysisRequest(
            transcript_path=self.temp_vtt.name,
            analysis_types=["executive_summary", "pedagogical_analysis"]
        )
        
        yield
        
        # Teardown
        os.unlink(self.temp_vtt.name)
    
    @patch('app.services.analysis.Anthropic')
    async def test_call_claude(self, mock_anthropic):
        """Test calling Claude API."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Claude's response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        # Call function
        result = await call_claude("Test prompt")
        
        # Verify Claude was called correctly
        mock_client.messages.create.assert_called_once()
        assert result == "Claude's response"
    
    @patch('app.services.analysis.call_claude')
    async def test_generate_executive_summary(self, mock_call_claude):
        """Test generating executive summary."""
        # Setup mock
        mock_call_claude.return_value = "Executive summary"
        
        # Call function
        result = await generate_executive_summary("Transcript text")
        
        # Verify Claude was called
        mock_call_claude.assert_called_once()
        assert result == "Executive summary"
    
    @patch('app.services.analysis.call_claude')
    async def test_generate_pedagogical_analysis(self, mock_call_claude):
        """Test generating pedagogical analysis."""
        # Setup mock
        mock_call_claude.return_value = "Pedagogical analysis"
        
        # Call function
        result = await generate_pedagogical_analysis("Transcript text")
        
        # Verify Claude was called
        mock_call_claude.assert_called_once()
        assert result == "Pedagogical analysis"
    
    @patch('app.services.analysis.call_claude')
    async def test_generate_aha_moments(self, mock_call_claude):
        """Test generating AHA moments."""
        # Setup mock
        mock_call_claude.return_value = "AHA moments"
        
        # Call function
        result = await generate_aha_moments("Transcript text")
        
        # Verify Claude was called
        mock_call_claude.assert_called_once()
        assert result == "AHA moments"
    
    @patch('app.services.analysis.call_claude')
    async def test_generate_engagement_analysis(self, mock_call_claude):
        """Test generating engagement analysis."""
        # Setup mock
        mock_call_claude.return_value = "Engagement analysis"
        
        # Call function
        result = await generate_engagement_analysis(
            "Transcript text",
            self.sample_segments,
            {"John Smith": "University A", "Jane Doe": "University B"}
        )
        
        # Verify Claude was called
        mock_call_claude.assert_called_once()
        assert "qualitative_analysis" in result
        assert result["qualitative_analysis"] == "Engagement analysis"
        assert "speaker_statistics" in result
        assert "school_mapping" in result
    
    @patch('app.services.analysis.parse_vtt')
    @patch('app.services.analysis.generate_executive_summary')
    @patch('app.services.analysis.generate_pedagogical_analysis')
    async def test_generate_analysis(self, mock_pedagogical, mock_executive, mock_parse_vtt):
        """Test generating complete analysis."""
        # Setup mocks
        mock_parse_vtt.return_value = self.sample_segments
        mock_executive.return_value = "Executive summary"
        mock_pedagogical.return_value = "Pedagogical analysis"
        
        # Call function
        result = await generate_analysis(self.sample_request)
        
        # Verify results
        assert result.executive_summary == "Executive summary"
        assert result.pedagogical_analysis == "Pedagogical analysis"
        assert result.aha_moments is None
        assert result.engagement_metrics is None


if __name__ == "__main__":
    unittest.main() 