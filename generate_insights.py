#!/usr/bin/env python3
"""
Script to generate insights from a real VTT file using our analysis service.
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the VTT parser
from app.services.vtt_parser import parse_vtt, merge_consecutive_segments

# Import Anthropic client
from anthropic import Anthropic

async def generate_insights(vtt_file):
    """Generate insights from a VTT file."""
    # Parse the VTT file
    print("Parsing VTT file...")
    segments = parse_vtt(vtt_file)
    merged_segments = merge_consecutive_segments(segments)
    
    # Format transcript for Claude
    print("Formatting transcript for Claude...")
    formatted_transcript = format_transcript_for_claude(merged_segments)
    
    # Get the API key from environment
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Initialize Claude client
    client = Anthropic(api_key=api_key)
    
    # Generate executive summary
    print("\nGenerating executive summary...")
    executive_summary = await generate_executive_summary(client, formatted_transcript)
    
    # Generate pedagogical analysis
    print("Generating pedagogical analysis...")
    pedagogical_analysis = await generate_pedagogical_analysis(client, formatted_transcript)
    
    # Generate AHA moments
    print("Generating AHA moments...")
    aha_moments = await generate_aha_moments(client, formatted_transcript)
    
    # Save the results to files
    os.makedirs("insights", exist_ok=True)
    
    # Save the executive summary
    print("\nSaving executive summary...")
    with open("insights/executive_summary.md", "w") as f:
        f.write(executive_summary)
    
    # Save the pedagogical analysis
    print("Saving pedagogical analysis...")
    with open("insights/pedagogical_analysis.md", "w") as f:
        f.write(pedagogical_analysis)
    
    # Save the AHA moments
    print("Saving AHA moments...")
    with open("insights/aha_moments.md", "w") as f:
        f.write(aha_moments)
    
    print("\nDone! Results saved to the 'insights' directory.")

def format_transcript_for_claude(segments):
    """Format transcript segments for Claude prompt."""
    formatted_lines = []
    
    for segment in segments:
        speaker = segment.speaker or "Unknown Speaker"
        time_range = f"[{segment.start_time} - {segment.end_time}]"
        formatted_lines.append(f"{time_range} {speaker}: {segment.text}")
    
    return "\n\n".join(formatted_lines)

async def call_claude(client, prompt):
    """Call Claude API with a prompt."""
    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        raise

async def generate_executive_summary(client, transcript_text):
    """Generate executive summary using Claude."""
    prompt = """
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
""".format(transcript=transcript_text[:30000])  # Limit transcript length
    
    return await call_claude(client, prompt)

async def generate_pedagogical_analysis(client, transcript_text):
    """Generate pedagogical analysis using Claude."""
    prompt = """
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
""".format(transcript=transcript_text[:30000])  # Limit transcript length
    
    return await call_claude(client, prompt)

async def generate_aha_moments(client, transcript_text):
    """Generate AHA moments analysis using Claude."""
    prompt = """
Identify 3-5 "AHA moments" in this educational session transcript.
For each moment:
1. Quote the relevant exchange
2. Explain why this represents a breakthrough in understanding
3. Note the teaching technique that facilitated this insight
4. Suggest how similar moments could be cultivated in future sessions

Transcript:
{transcript}
""".format(transcript=transcript_text[:30000])  # Limit transcript length
    
    return await call_claude(client, prompt)

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
        await generate_insights(vtt_file)
    except Exception as e:
        print(f"\nError generating insights: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 