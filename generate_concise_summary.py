#!/usr/bin/env python3
"""
Script to generate a concise summary (6-10 lines) for school leaders.
"""

import os
import sys
import asyncio

# Import Anthropic client
from anthropic import Anthropic

async def generate_concise_summary(vtt_file=None, existing_summary=None):
    """Generate a concise summary for school leaders."""
    # Get the API key from environment
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY environment variable not set.")
        return None
    
    # Initialize Claude client
    client = Anthropic(api_key=api_key)
    
    # Determine the input source
    if vtt_file and os.path.exists(vtt_file):
        print(f"Reading executive summary from insights/executive_summary.md...")
        if os.path.exists("insights/executive_summary.md"):
            with open("insights/executive_summary.md", "r") as f:
                existing_summary = f.read()
        else:
            print("Error: insights/executive_summary.md not found.")
            print("Please run generate_insights.py first.")
            return None
    elif not existing_summary:
        print("Error: No input provided.")
        print("Please provide either a VTT file or an existing summary.")
        return None
    
    print("Generating concise summary...")
    
    # Create prompt for Claude
    prompt = """
You are tasked with creating an extremely concise summary of an educational session for school leaders.

The summary must be:
1. EXACTLY 6-10 lines (not bullet points)
2. Written as a single paragraph
3. Focused on the key topics, approaches, and outcomes
4. Clear and direct without academic jargon
5. Similar in style to this example:

Example:
"The meeting focused on introducing educators to generative AI tools and their applications in education, with demonstrations of various platforms like ChatGPT, Notebook LM, and other language models. Participants explored the capabilities and limitations of these tools, including their use in content creation, data analysis, and language translation, while also discussing the importance of providing clear prompts and verifying information. The session concluded with discussions on the differences between free and paid AI tool accounts, emphasizing the advanced features available in paid versions and encouraging participants to explore these tools further for educational purposes."

Here is the longer executive summary that needs to be condensed:

{summary}

Create ONLY the concise 6-10 line paragraph summary with no additional text, explanations, or headers.
""".format(summary=existing_summary)
    
    try:
        # Call Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        concise_summary = response.content[0].text.strip()
        
        # Save the concise summary
        os.makedirs("insights", exist_ok=True)
        with open("insights/concise_summary.md", "w") as f:
            f.write(concise_summary)
        
        print("\nConcise summary generated and saved to insights/concise_summary.md")
        print("\nHere's the concise summary:")
        print("-" * 80)
        print(concise_summary)
        print("-" * 80)
        
        return concise_summary
    
    except Exception as e:
        print(f"\nError generating concise summary: {e}")
        return None

async def main():
    """Main function."""
    # Check if we have insights from previous run
    if os.path.exists("insights/executive_summary.md"):
        await generate_concise_summary(vtt_file="June 28 Session 3 Primary Math MMM Transcript.vtt")
    else:
        print("No existing executive summary found.")
        print("Please run generate_insights.py first.")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 