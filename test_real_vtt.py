#!/usr/bin/env python3
"""
Script to test the VTT parser with a real VTT file.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the VTT parser
from app.services.vtt_parser import (
    parse_vtt, 
    extract_meeting_metadata, 
    calculate_speaker_stats, 
    merge_consecutive_segments
)

def main():
    """Test the VTT parser with a real VTT file."""
    # Path to the VTT file
    vtt_file = "June 28 Session 3 Primary Math MMM Transcript.vtt"
    
    # Check if the file exists
    if not os.path.exists(vtt_file):
        print(f"Error: File '{vtt_file}' not found.")
        sys.exit(1)
    
    print(f"Processing file: {vtt_file}")
    
    # Parse the VTT file
    print("Parsing VTT file...")
    segments = parse_vtt(vtt_file)
    print(f"Found {len(segments)} segments.")
    
    # Extract meeting metadata
    print("\nExtracting meeting metadata...")
    topic, host = extract_meeting_metadata(segments)
    print(f"Topic: {topic}")
    print(f"Host: {host}")
    
    # Calculate speaker statistics
    print("\nCalculating speaker statistics...")
    stats = calculate_speaker_stats(segments)
    
    # Print speaker statistics
    print(f"Found {len(stats)} speakers:")
    for speaker, speaker_stats in stats.items():
        print(f"  {speaker}:")
        print(f"    Segments: {speaker_stats['total_segments']}")
        print(f"    Words: {speaker_stats['total_words']}")
        print(f"    Duration: {speaker_stats['total_duration_seconds']:.2f} seconds")
    
    # Merge consecutive segments
    print("\nMerging consecutive segments...")
    merged_segments = merge_consecutive_segments(segments)
    print(f"Merged into {len(merged_segments)} segments.")
    
    # Save the results to a JSON file
    print("\nSaving results to 'vtt_analysis_results.json'...")
    
    # Convert segments to dictionaries
    segments_dict = [segment.model_dump() for segment in segments[:10]]
    merged_segments_dict = [segment.model_dump() for segment in merged_segments[:10]]
    
    # Create the results dictionary
    results = {
        "file": vtt_file,
        "analysis_time": datetime.now().isoformat(),
        "total_segments": len(segments),
        "merged_segments": len(merged_segments),
        "topic": topic,
        "host": host,
        "speakers": list(stats.keys()),
        "speaker_stats": stats,
        "sample_segments": segments_dict,
        "sample_merged_segments": merged_segments_dict
    }
    
    # Save the results to a JSON file
    with open("vtt_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Done!")

if __name__ == "__main__":
    main() 