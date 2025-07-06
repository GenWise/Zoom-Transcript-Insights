#!/usr/bin/env python3
"""
Script to generate engagement metrics from a VTT file.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the VTT parser
from app.services.vtt_parser import parse_vtt, calculate_speaker_stats

# Import Anthropic client
from anthropic import Anthropic

async def generate_engagement_metrics(vtt_file):
    """Generate engagement metrics from a VTT file."""
    # Parse the VTT file
    print("Parsing VTT file...")
    segments = parse_vtt(vtt_file)
    
    # Calculate speaker statistics
    print("Calculating speaker statistics...")
    speaker_stats = calculate_speaker_stats(segments)
    
    # Identify top speakers
    top_speakers = sorted(
        speaker_stats.items(), 
        key=lambda x: x[1]["total_duration_seconds"], 
        reverse=True
    )[:10]  # Top 10 speakers
    
    # Create engagement metrics
    engagement_metrics = {
        "file": vtt_file,
        "analysis_time": datetime.now().isoformat(),
        "total_segments": len(segments),
        "total_speakers": len(speaker_stats),
        "total_duration_seconds": sum(stats["total_duration_seconds"] for stats in speaker_stats.values()),
        "total_words": sum(stats["total_words"] for stats in speaker_stats.values()),
        "speaker_stats": speaker_stats,
        "top_speakers": {name: stats for name, stats in top_speakers}
    }
    
    # Calculate participation metrics
    participation_metrics = calculate_participation_metrics(segments, speaker_stats)
    engagement_metrics.update(participation_metrics)
    
    # Generate visualizations
    print("Generating visualizations...")
    generate_visualizations(speaker_stats)
    
    # Get qualitative analysis from Claude
    print("Generating qualitative analysis...")
    qualitative_analysis = await generate_qualitative_analysis(segments, speaker_stats)
    engagement_metrics["qualitative_analysis"] = qualitative_analysis
    
    # Save the engagement metrics
    os.makedirs("insights", exist_ok=True)
    with open("insights/engagement_metrics.json", "w") as f:
        json.dump(engagement_metrics, f, indent=2, default=str)
    
    # Create a human-readable summary
    create_human_readable_summary(engagement_metrics)
    
    print("\nEngagement metrics generated and saved to insights/engagement_metrics.json")
    print("Visualizations saved to insights/visualizations/")
    print("Human-readable summary saved to insights/engagement_summary.md")
    
    return engagement_metrics

def calculate_participation_metrics(segments, speaker_stats):
    """Calculate participation metrics from segments."""
    # Initialize metrics
    metrics = {
        "participation_distribution": {},
        "interaction_patterns": {},
        "engagement_over_time": {}
    }
    
    # Calculate participation distribution (percentage of total time)
    total_duration = sum(stats["total_duration_seconds"] for stats in speaker_stats.values())
    if total_duration > 0:
        metrics["participation_distribution"] = {
            name: (stats["total_duration_seconds"] / total_duration) * 100
            for name, stats in speaker_stats.items()
        }
    
    # Calculate interaction patterns (who speaks after whom)
    interactions = defaultdict(lambda: defaultdict(int))
    for i in range(1, len(segments)):
        if segments[i-1].speaker and segments[i].speaker:
            interactions[segments[i-1].speaker][segments[i].speaker] += 1
    
    metrics["interaction_patterns"] = {
        speaker: dict(interactions_dict)
        for speaker, interactions_dict in interactions.items()
    }
    
    # Calculate engagement over time (segments per 5-minute window)
    if segments:
        # Get the start and end times
        start_time_parts = segments[0].start_time.split(':')
        start_seconds = int(start_time_parts[0]) * 3600 + int(start_time_parts[1]) * 60 + float(start_time_parts[2])
        
        end_time_parts = segments[-1].end_time.split(':')
        end_seconds = int(end_time_parts[0]) * 3600 + int(end_time_parts[1]) * 60 + float(end_time_parts[2])
        
        # Create 5-minute windows
        window_size = 300  # 5 minutes in seconds
        windows = {}
        
        for segment in segments:
            segment_start_parts = segment.start_time.split(':')
            segment_start_seconds = int(segment_start_parts[0]) * 3600 + int(segment_start_parts[1]) * 60 + float(segment_start_parts[2])
            
            # Calculate which window this segment belongs to
            window_index = int((segment_start_seconds - start_seconds) / window_size)
            window_start = start_seconds + (window_index * window_size)
            window_end = window_start + window_size
            
            # Format window label
            window_start_min = int(window_start / 60)
            window_end_min = int(window_end / 60)
            window_label = f"{window_start_min}-{window_end_min} min"
            
            # Initialize window if needed
            if window_label not in windows:
                windows[window_label] = defaultdict(int)
            
            # Increment segment count for this speaker in this window
            if segment.speaker:
                windows[window_label][segment.speaker] += 1
            else:
                windows[window_label]["Unknown"] += 1
        
        metrics["engagement_over_time"] = {
            window_label: dict(speaker_counts)
            for window_label, speaker_counts in sorted(windows.items())
        }
    
    return metrics

def generate_visualizations(speaker_stats):
    """Generate visualizations for engagement metrics."""
    # Create directory for visualizations
    os.makedirs("insights/visualizations", exist_ok=True)
    
    # 1. Speaking time by participant
    plt.figure(figsize=(12, 8))
    
    # Sort speakers by speaking time
    sorted_speakers = sorted(
        speaker_stats.items(),
        key=lambda x: x[1]["total_duration_seconds"],
        reverse=True
    )[:10]  # Top 10 speakers
    
    names = [name for name, _ in sorted_speakers]
    durations = [stats["total_duration_seconds"] / 60 for _, stats in sorted_speakers]  # Convert to minutes
    
    plt.barh(names, durations)
    plt.xlabel("Speaking Time (minutes)")
    plt.ylabel("Participant")
    plt.title("Speaking Time by Participant (Top 10)")
    plt.tight_layout()
    plt.savefig("insights/visualizations/speaking_time.png")
    
    # 2. Word count by participant
    plt.figure(figsize=(12, 8))
    
    # Sort speakers by word count
    sorted_speakers = sorted(
        speaker_stats.items(),
        key=lambda x: x[1]["total_words"],
        reverse=True
    )[:10]  # Top 10 speakers
    
    names = [name for name, _ in sorted_speakers]
    word_counts = [stats["total_words"] for _, stats in sorted_speakers]
    
    plt.barh(names, word_counts)
    plt.xlabel("Word Count")
    plt.ylabel("Participant")
    plt.title("Word Count by Participant (Top 10)")
    plt.tight_layout()
    plt.savefig("insights/visualizations/word_count.png")
    
    # 3. Participation distribution pie chart
    plt.figure(figsize=(10, 10))
    
    # Calculate total duration
    total_duration = sum(stats["total_duration_seconds"] for stats in speaker_stats.values())
    
    # Sort speakers by speaking time
    sorted_speakers = sorted(
        speaker_stats.items(),
        key=lambda x: x[1]["total_duration_seconds"],
        reverse=True
    )
    
    # Get top 5 speakers and group the rest as "Others"
    top_speakers = sorted_speakers[:5]
    other_speakers = sorted_speakers[5:]
    
    names = [name for name, _ in top_speakers]
    durations = [stats["total_duration_seconds"] for _, stats in top_speakers]
    
    # Add "Others" category if there are more than 5 speakers
    if other_speakers:
        names.append("Others")
        durations.append(sum(stats["total_duration_seconds"] for _, stats in other_speakers))
    
    # Calculate percentages
    percentages = [duration / total_duration * 100 for duration in durations]
    
    plt.pie(percentages, labels=names, autopct='%1.1f%%')
    plt.title("Participation Distribution")
    plt.savefig("insights/visualizations/participation_distribution.png")

def create_human_readable_summary(metrics):
    """Create a human-readable summary of engagement metrics."""
    summary = "# Engagement Metrics Summary\n\n"
    
    # Basic statistics
    summary += "## Basic Statistics\n\n"
    summary += f"- **Total Segments**: {metrics['total_segments']}\n"
    summary += f"- **Total Speakers**: {metrics['total_speakers']}\n"
    summary += f"- **Total Duration**: {metrics['total_duration_seconds'] / 60:.2f} minutes\n"
    summary += f"- **Total Words**: {metrics['total_words']}\n\n"
    
    # Top speakers
    summary += "## Top Speakers\n\n"
    summary += "| Speaker | Speaking Time (min) | Word Count | Segments |\n"
    summary += "|---------|---------------------|-----------|----------|\n"
    
    for name, stats in list(metrics['top_speakers'].items())[:5]:  # Top 5 speakers
        summary += f"| {name} | {stats['total_duration_seconds'] / 60:.2f} | {stats['total_words']} | {stats['total_segments']} |\n"
    
    summary += "\n"
    
    # Participation distribution
    summary += "## Participation Distribution\n\n"
    summary += "| Speaker | Percentage of Total Time |\n"
    summary += "|---------|---------------------------|\n"
    
    # Sort by percentage
    sorted_participation = sorted(
        metrics['participation_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]  # Top 5 speakers
    
    for name, percentage in sorted_participation:
        summary += f"| {name} | {percentage:.2f}% |\n"
    
    summary += "\n"
    
    # Qualitative analysis
    if "qualitative_analysis" in metrics:
        summary += "## Qualitative Analysis\n\n"
        summary += metrics["qualitative_analysis"]
        summary += "\n\n"
    
    # Add links to visualizations
    summary += "## Visualizations\n\n"
    summary += "- [Speaking Time by Participant](visualizations/speaking_time.png)\n"
    summary += "- [Word Count by Participant](visualizations/word_count.png)\n"
    summary += "- [Participation Distribution](visualizations/participation_distribution.png)\n"
    
    # Save the summary
    with open("insights/engagement_summary.md", "w") as f:
        f.write(summary)

async def generate_qualitative_analysis(segments, speaker_stats):
    """Generate qualitative analysis of engagement using Claude."""
    # Get the API key from environment
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY environment variable not set.")
        return "No qualitative analysis available (API key not set)."
    
    # Format speaker stats for Claude
    stats_summary = "\n".join([
        f"- {name}: {stats['total_segments']} segments, {stats['total_words']} words, {stats['total_duration_seconds'] / 60:.2f} minutes"
        for name, stats in sorted(
            speaker_stats.items(),
            key=lambda x: x[1]["total_duration_seconds"],
            reverse=True
        )[:10]  # Top 10 speakers
    ])
    
    # Create prompt for Claude
    prompt = f"""
You are analyzing the engagement patterns in an educational session. 
Based on the following speaker statistics, provide a brief qualitative analysis of engagement patterns.

Speaker Statistics (Top 10 participants by speaking time):
{stats_summary}

In your analysis, please address:
1. The balance of participation among speakers
2. Any notable patterns in engagement
3. Suggestions for improving engagement in future sessions

Keep your analysis concise (about 200-300 words) and focused on engagement patterns.
"""
    
    try:
        # Initialize Claude client
        client = Anthropic(api_key=api_key)
        
        # Call Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text.strip()
    
    except Exception as e:
        print(f"Error generating qualitative analysis: {e}")
        return "Error generating qualitative analysis."

async def main():
    """Main function."""
    # Path to the VTT file
    vtt_file = "June 28 Session 3 Primary Math MMM Transcript.vtt"
    
    # Check if the file exists
    if not os.path.exists(vtt_file):
        print(f"Error: File '{vtt_file}' not found.")
        sys.exit(1)
    
    print(f"Processing file: {vtt_file}")
    print("(This may take a while as it involves API calls to Claude)")
    
    try:
        await generate_engagement_metrics(vtt_file)
    except Exception as e:
        print(f"\nError generating engagement metrics: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 