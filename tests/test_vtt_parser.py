import unittest
import os
import tempfile
from typing import List

from app.models.schemas import TranscriptSegment
from app.services.vtt_parser import (
    parse_vtt, 
    extract_meeting_metadata, 
    calculate_speaker_stats, 
    merge_consecutive_segments
)

class TestVTTParser(unittest.TestCase):
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

00:00:16.000 --> 00:00:20.000
This is a segment without speaker information.

00:00:21.000 --> 00:00:25.000
Meeting title: Advanced Python Programming

00:00:26.000 --> 00:00:30.000
Hosted by: John Smith
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
            ),
            TranscriptSegment(
                start_time="00:00:16.000",
                end_time="00:00:20.000",
                speaker=None,
                text="This is a segment without speaker information."
            ),
            TranscriptSegment(
                start_time="00:00:21.000",
                end_time="00:00:25.000",
                speaker=None,
                text="Meeting title: Advanced Python Programming"
            ),
            TranscriptSegment(
                start_time="00:00:26.000",
                end_time="00:00:30.000",
                speaker=None,
                text="Hosted by: John Smith"
            )
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_vtt.name)
    
    def test_parse_vtt(self):
        """Test parsing a VTT file."""
        segments = parse_vtt(self.temp_vtt.name)
        
        # Check we have the correct number of segments
        self.assertEqual(len(segments), 6)
        
        # Check the first segment
        self.assertEqual(segments[0].start_time, "00:00:00.000")
        self.assertEqual(segments[0].end_time, "00:00:05.000")
        self.assertEqual(segments[0].speaker, "John Smith")
        self.assertEqual(segments[0].text, "Hello everyone, welcome to the meeting.")
        
        # Check a segment without speaker info
        self.assertEqual(segments[3].speaker, None)
        self.assertEqual(segments[3].text, "This is a segment without speaker information.")
    
    def test_extract_meeting_metadata(self):
        """Test extracting meeting metadata from segments."""
        topic, host = extract_meeting_metadata(self.sample_segments)
        
        self.assertEqual(topic, "Advanced Python Programming")
        self.assertEqual(host, "John Smith")
    
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
        
        # Check Jane Doe's stats
        self.assertEqual(stats["Jane Doe"]["total_segments"], 1)
        self.assertEqual(stats["Jane Doe"]["total_words"], 9)
        self.assertAlmostEqual(stats["Jane Doe"]["total_duration_seconds"], 4.0)
    
    def test_merge_consecutive_segments(self):
        """Test merging consecutive segments from the same speaker."""
        # Create a simpler set of segments for testing merge functionality
        test_segments = [
            TranscriptSegment(
                start_time="00:00:00.000",
                end_time="00:00:05.000",
                speaker="John Smith",
                text="Hello everyone."
            ),
            TranscriptSegment(
                start_time="00:00:06.000",
                end_time="00:00:10.000",
                speaker="John Smith",
                text="Welcome to the meeting."
            ),
            TranscriptSegment(
                start_time="00:00:11.000",
                end_time="00:00:15.000",
                speaker="Jane Doe",
                text="Thanks John."
            )
        ]
        
        merged = merge_consecutive_segments(test_segments)
        
        # Check that consecutive segments from John Smith are merged
        self.assertEqual(len(merged), 2)  # 2 segments after merging
        
        # Check the merged segment
        self.assertEqual(merged[0].start_time, "00:00:00.000")
        self.assertEqual(merged[0].end_time, "00:00:10.000")
        self.assertEqual(merged[0].speaker, "John Smith")
        self.assertEqual(merged[0].text, "Hello everyone. Welcome to the meeting.")

if __name__ == "__main__":
    unittest.main() 