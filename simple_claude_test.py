#!/usr/bin/env python3
"""
Simple test script for the Claude API.
"""

import os
import sys
import anthropic
from anthropic import Anthropic

def main():
    """Test the Claude API."""
    # Get the API key from environment
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY environment variable not set.")
        sys.exit(1)
    
    print(f"Using API key: {api_key[:10]}...")
    
    try:
        # Initialize the client
        client = Anthropic(api_key=api_key)
        
        # Send a simple message
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": "Hello, Claude! Please summarize the benefits of unit testing in 3 bullet points."}
            ]
        )
        
        # Print the response
        print("\nClaude's response:")
        print(response.content[0].text)
        
        print("\nAPI call successful!")
    
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 