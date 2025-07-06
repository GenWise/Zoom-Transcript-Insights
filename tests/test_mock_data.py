import unittest
import os
import tempfile
import json
from typing import Dict, List

from app.models.schemas import TranscriptSegment, Transcript, SessionMetadata, AnalysisResult
from datetime import datetime

class TestMockData(unittest.TestCase):
    """Tests for generating mock data for testing purposes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_generate_mock_transcript(self):
        """Test generating a mock transcript."""
        # Generate mock transcript
        transcript = self._generate_mock_transcript()
        
        # Verify transcript properties
        self.assertEqual(transcript.meeting_id, "mock-meeting-123")
        self.assertEqual(transcript.topic, "Mock Course Session")
        self.assertEqual(len(transcript.segments), 10)
        
        # Save to file
        output_path = os.path.join(self.output_dir, "mock_transcript.json")
        with open(output_path, "w") as f:
            f.write(transcript.model_dump_json(indent=2))
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
    
    def test_generate_mock_analysis_result(self):
        """Test generating a mock analysis result."""
        # Generate mock analysis result
        result = self._generate_mock_analysis_result()
        
        # Verify result properties
        self.assertIsNotNone(result.executive_summary)
        self.assertIsNotNone(result.pedagogical_analysis)
        self.assertIsNotNone(result.aha_moments)
        self.assertIsNotNone(result.engagement_metrics)
        
        # Save to file
        output_path = os.path.join(self.output_dir, "mock_analysis.json")
        with open(output_path, "w") as f:
            f.write(result.model_dump_json(indent=2))
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
    
    def test_generate_mock_vtt_file(self):
        """Test generating a mock VTT file."""
        # Generate mock VTT content
        vtt_content = self._generate_mock_vtt_content()
        
        # Save to file
        output_path = os.path.join(self.output_dir, "mock_transcript.vtt")
        with open(output_path, "w") as f:
            f.write(vtt_content)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content
        with open(output_path, "r") as f:
            content = f.read()
        
        self.assertIn("WEBVTT", content)
        self.assertIn("Instructor:", content)
        self.assertIn("Student 1:", content)
    
    def _generate_mock_transcript(self) -> Transcript:
        """Generate a mock transcript for testing."""
        segments = []
        
        # Create 10 mock segments
        speakers = ["Instructor", "Student 1", "Student 2"]
        for i in range(10):
            speaker_idx = i % len(speakers)
            start_seconds = i * 30
            end_seconds = start_seconds + 25
            
            start_time = f"{start_seconds // 3600:02d}:{(start_seconds % 3600) // 60:02d}:{start_seconds % 60:02d}.000"
            end_time = f"{end_seconds // 3600:02d}:{(end_seconds % 3600) // 60:02d}:{end_seconds % 60:02d}.000"
            
            segment = TranscriptSegment(
                start_time=start_time,
                end_time=end_time,
                speaker=speakers[speaker_idx],
                text=f"This is mock text for segment {i+1}."
            )
            segments.append(segment)
        
        return Transcript(
            meeting_id="mock-meeting-123",
            topic="Mock Course Session",
            start_time=datetime.now(),
            duration=300,
            segments=segments
        )
    
    def _generate_mock_analysis_result(self) -> AnalysisResult:
        """Generate a mock analysis result for testing."""
        return AnalysisResult(
            executive_summary="This is a mock executive summary of the session.",
            pedagogical_analysis="This is a mock pedagogical analysis that would normally be 1.5 pages long.",
            aha_moments="AHA Moment 1: Student 1 had a breakthrough understanding of the concept.\nAHA Moment 2: Student 2 connected previous knowledge to new material.",
            engagement_metrics={
                "speaker_statistics": {
                    "Instructor": {
                        "total_segments": 5,
                        "total_words": 250,
                        "total_duration_seconds": 150
                    },
                    "Student 1": {
                        "total_segments": 3,
                        "total_words": 120,
                        "total_duration_seconds": 90
                    },
                    "Student 2": {
                        "total_segments": 2,
                        "total_words": 80,
                        "total_duration_seconds": 60
                    }
                },
                "qualitative_analysis": "This is a mock qualitative analysis of engagement.",
                "school_mapping": {
                    "Instructor": "University X",
                    "Student 1": "University Y",
                    "Student 2": "University Z"
                }
            }
        )
    
    def _generate_mock_vtt_content(self) -> str:
        """Generate mock VTT content for testing."""
        return """WEBVTT

00:00:00.000 --> 00:00:10.000
Instructor: Welcome to our mock session. Today we'll be discussing important concepts.

00:00:15.000 --> 00:00:25.000
Student 1: I have a question about the first topic.

00:00:30.000 --> 00:00:45.000
Instructor: That's a great question. Let me explain in more detail.

00:00:50.000 --> 00:01:00.000
Student 2: I'm still confused about one aspect.

00:01:05.000 --> 00:01:20.000
Instructor: Let me clarify that. The key point to understand is...

00:01:25.000 --> 00:01:35.000
Student 1: Oh, now I understand! That makes so much more sense.

00:01:40.000 --> 00:01:50.000
Instructor: Excellent! Let's move on to the next topic.
"""

if __name__ == "__main__":
    unittest.main() 