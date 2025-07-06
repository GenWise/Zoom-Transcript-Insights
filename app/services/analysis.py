import logging
import json
from typing import Dict, Any, List, Optional
import asyncio

import anthropic
from anthropic import Anthropic

import config
from app.models.schemas import AnalysisRequest, AnalysisResult, TranscriptSegment
from app.services.vtt_parser import parse_vtt, merge_consecutive_segments

logger = logging.getLogger(__name__)

async def generate_analysis(request: AnalysisRequest) -> AnalysisResult:
    """
    Generate analysis for a transcript.
    
    Args:
        request: Analysis request with transcript path and options
        
    Returns:
        Analysis result with generated insights
    """
    try:
        # Parse the transcript
        segments = parse_vtt(request.transcript_path)
        merged_segments = merge_consecutive_segments(segments)
        
        # Format transcript for Claude
        transcript_text = format_transcript_for_claude(merged_segments)
        
        # Initialize result
        result = AnalysisResult()
        
        # Generate each requested analysis type
        tasks = []
        
        if "executive_summary" in request.analysis_types:
            tasks.append(generate_executive_summary(transcript_text))
        
        if "pedagogical_analysis" in request.analysis_types:
            tasks.append(generate_pedagogical_analysis(transcript_text))
        
        if "aha_moments" in request.analysis_types:
            tasks.append(generate_aha_moments(transcript_text))
        
        if "engagement_analysis" in request.analysis_types:
            school_mapping = {}
            if request.participant_school_mapping:
                school_mapping = request.participant_school_mapping
            tasks.append(generate_engagement_analysis(transcript_text, segments, school_mapping))
        
        # Wait for all tasks to complete
        analysis_results = await asyncio.gather(*tasks)
        
        # Assign results to the appropriate fields
        for i, analysis_type in enumerate([t for t in request.analysis_types if t in ["executive_summary", "pedagogical_analysis", "aha_moments", "engagement_analysis"]]):
            if analysis_type == "executive_summary":
                result.executive_summary = analysis_results[i]
            elif analysis_type == "pedagogical_analysis":
                result.pedagogical_analysis = analysis_results[i]
            elif analysis_type == "aha_moments":
                result.aha_moments = analysis_results[i]
            elif analysis_type == "engagement_analysis":
                result.engagement_metrics = analysis_results[i]
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating analysis: {e}")
        raise

def format_transcript_for_claude(segments: List[TranscriptSegment]) -> str:
    """
    Format transcript segments for Claude prompt.
    
    Args:
        segments: List of transcript segments
        
    Returns:
        Formatted transcript text
    """
    formatted_lines = []
    
    for segment in segments:
        speaker = segment.speaker or "Unknown Speaker"
        time_range = f"[{segment.start_time} - {segment.end_time}]"
        formatted_lines.append(f"{time_range} {speaker}: {segment.text}")
    
    return "\n\n".join(formatted_lines)

async def call_claude(prompt: str) -> str:
    """
    Call Claude API with a prompt.
    
    Args:
        prompt: Prompt to send to Claude
        
    Returns:
        Claude's response
    """
    try:
        client = Anthropic(api_key=config.CLAUDE_API_KEY)
        
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        raise

async def generate_executive_summary(transcript_text: str) -> str:
    """
    Generate executive summary using Claude.
    
    Args:
        transcript_text: Formatted transcript text
        
    Returns:
        Executive summary
    """
    prompt = config.CLAUDE_PROMPTS["executive_summary"].format(transcript=transcript_text)
    return await call_claude(prompt)

async def generate_pedagogical_analysis(transcript_text: str) -> str:
    """
    Generate pedagogical analysis using Claude.
    
    Args:
        transcript_text: Formatted transcript text
        
    Returns:
        Pedagogical analysis
    """
    prompt = config.CLAUDE_PROMPTS["pedagogical_analysis"].format(transcript=transcript_text)
    return await call_claude(prompt)

async def generate_aha_moments(transcript_text: str) -> str:
    """
    Generate AHA moments analysis using Claude.
    
    Args:
        transcript_text: Formatted transcript text
        
    Returns:
        AHA moments analysis
    """
    prompt = config.CLAUDE_PROMPTS["aha_moments"].format(transcript=transcript_text)
    return await call_claude(prompt)

async def generate_engagement_analysis(
    transcript_text: str,
    segments: List[TranscriptSegment],
    school_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Generate engagement analysis using Claude and calculate statistics.
    
    Args:
        transcript_text: Formatted transcript text
        segments: List of transcript segments
        school_mapping: Mapping of participant names to schools
        
    Returns:
        Engagement metrics and analysis
    """
    # Calculate basic statistics
    speaker_stats = calculate_speaker_stats(segments)
    
    # Format school mapping for Claude
    school_mapping_text = json.dumps(school_mapping, indent=2)
    
    # Generate qualitative analysis with Claude
    prompt = config.CLAUDE_PROMPTS["engagement_analysis"].format(
        transcript=transcript_text,
        school_mapping=school_mapping_text
    )
    
    qualitative_analysis = await call_claude(prompt)
    
    # Combine statistics and qualitative analysis
    result = {
        "speaker_statistics": speaker_stats,
        "qualitative_analysis": qualitative_analysis,
        "school_mapping": school_mapping
    }
    
    return result

def calculate_speaker_stats(segments: List[TranscriptSegment]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate statistics for each speaker.
    
    Args:
        segments: List of transcript segments
        
    Returns:
        Dictionary with speaker statistics
    """
    stats = {}
    
    for segment in segments:
        if not segment.speaker:
            continue
        
        speaker = segment.speaker
        if speaker not in stats:
            stats[speaker] = {
                "total_segments": 0,
                "total_words": 0,
                "total_duration_seconds": 0,
                "first_timestamp": segment.start_time,
                "last_timestamp": segment.end_time
            }
        
        # Update stats
        stats[speaker]["total_segments"] += 1
        stats[speaker]["total_words"] += len(segment.text.split())
        
        # Calculate duration
        start_time_parts = segment.start_time.split(':')
        end_time_parts = segment.end_time.split(':')
        
        start_seconds = int(start_time_parts[0]) * 3600 + int(start_time_parts[1]) * 60 + float(start_time_parts[2])
        end_seconds = int(end_time_parts[0]) * 3600 + int(end_time_parts[1]) * 60 + float(end_time_parts[2])
        
        duration = end_seconds - start_seconds
        stats[speaker]["total_duration_seconds"] += duration
        
        # Update last timestamp
        stats[speaker]["last_timestamp"] = segment.end_time
    
    return stats 