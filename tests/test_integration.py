import unittest
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

from app.models.schemas import AnalysisRequest, AnalysisResult
from app.services.analysis import generate_analysis
from app.services.vtt_parser import parse_vtt

class TestIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary VTT file for testing
        self.temp_vtt = tempfile.NamedTemporaryFile(suffix=".vtt", delete=False)
        with open(self.temp_vtt.name, "w") as f:
            f.write("""WEBVTT

00:00:00.000 --> 00:00:05.000
Professor: Welcome to our session on machine learning fundamentals.

00:00:06.000 --> 00:00:10.000
Professor: Today we'll be covering neural networks and their applications.

00:00:11.000 --> 00:00:15.000
Student A: Can you explain backpropagation in more detail?

00:00:16.000 --> 00:00:25.000
Professor: Certainly. Backpropagation is the algorithm used to calculate gradients in neural networks.

00:00:26.000 --> 00:00:30.000
Student B: I'm still confused about activation functions.

00:00:31.000 --> 00:00:40.000
Professor: Let's take a step back. Activation functions introduce non-linearity into the network.

00:00:41.000 --> 00:00:45.000
Student A: Oh, I see now! That makes much more sense.
""")
        
        # Sample school mapping
        self.school_mapping = {
            "Professor": "University X",
            "Student A": "University Y",
            "Student B": "University Z"
        }
        
        # Sample analysis request
        self.sample_request = AnalysisRequest(
            transcript_path=self.temp_vtt.name,
            analysis_types=["executive_summary", "aha_moments"],
            participant_school_mapping=self.school_mapping
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_vtt.name)
    
    @patch('app.services.analysis.call_claude')
    def test_end_to_end_workflow(self, mock_call_claude):
        """Test the end-to-end workflow of processing a VTT file and generating insights."""
        # Setup mock for Claude API calls
        mock_call_claude.side_effect = [
            # Executive summary response
            "This session covered machine learning fundamentals, focusing on neural networks and backpropagation. The professor explained activation functions and their role in introducing non-linearity. Students showed engagement by asking clarifying questions. An 'aha moment' occurred when Student A gained clarity on the concepts.",
            # AHA moments response
            "AHA Moment 1:\n- Exchange: Student A asks about backpropagation, Professor explains, and later Student A exclaims 'Oh, I see now!'\n- Breakthrough: Student A gained clarity on backpropagation concepts after the professor's detailed explanation.\n- Teaching technique: Breaking down complex concepts and revisiting fundamentals when students express confusion."
        ]
        
        # Run the analysis
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(generate_analysis(self.sample_request))
        
        # Verify Claude was called twice (once for each analysis type)
        self.assertEqual(mock_call_claude.call_count, 2)
        
        # Check that the results contain the expected analysis types
        self.assertIsNotNone(result.executive_summary)
        self.assertIsNotNone(result.aha_moments)
        self.assertIsNone(result.pedagogical_analysis)
        self.assertIsNone(result.engagement_metrics)
        
        # Check content of results
        self.assertIn("machine learning fundamentals", result.executive_summary)
        self.assertIn("AHA Moment 1", result.aha_moments)
    
    def test_vtt_parsing_integration(self):
        """Test that VTT parsing works correctly in the integration flow."""
        # Parse the VTT file
        segments = parse_vtt(self.temp_vtt.name)
        
        # Check that we have the correct number of segments
        self.assertEqual(len(segments), 7)
        
        # Check that speakers are correctly extracted
        speakers = set(segment.speaker for segment in segments if segment.speaker)
        expected_speakers = {"Professor", "Student A", "Student B"}
        self.assertEqual(speakers, expected_speakers)
        
        # Check that the content is correctly extracted
        professor_segments = [s for s in segments if s.speaker == "Professor"]
        self.assertEqual(len(professor_segments), 4)  # There are 4 Professor segments in the VTT file
        self.assertIn("neural networks", professor_segments[1].text)

if __name__ == "__main__":
    unittest.main() 