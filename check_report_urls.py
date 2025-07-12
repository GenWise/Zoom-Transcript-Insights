#!/usr/bin/env python3
"""
Script to check if insight URLs are present in the Zoom Report.
"""

import os
import sys
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import config

def main():
    """Check the Zoom Report for insight URLs."""
    # Load environment variables
    load_dotenv()
    
    # Get the report ID
    report_id = os.environ.get("ZOOM_REPORT_ID")
    if not report_id:
        print("Error: ZOOM_REPORT_ID not found in environment variables.")
        sys.exit(1)
    
    print(f"Checking Zoom Report with ID: {report_id}")
    
    # Set up Google Sheets API client
    try:
        credentials = service_account.Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE, 
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheets_service = build("sheets", "v4", credentials=credentials)
        
        # Get sheet names first
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=report_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        
        if not sheets:
            print("No sheets found in the spreadsheet.")
            sys.exit(1)
            
        # Use the first sheet's title
        sheet_title = sheets[0]['properties']['title']
        print(f"Using sheet: {sheet_title}")
        
        # Get the spreadsheet values with the correct sheet name
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=report_id,
            range=f"{sheet_title}!A1:Q1000"  # Using explicit range with sheet name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("No data found in report.")
            sys.exit(1)
        
        # Convert to DataFrame for easier analysis
        headers = values[0]
        data = values[1:] if len(values) > 1 else []
        df = pd.DataFrame(data, columns=headers)
        
        # Check for insight URL columns
        insight_columns = [
            "Executive Summary URL", 
            "Pedagogical Analysis URL", 
            "Aha Moments URL", 
            "Engagement Metrics URL", 
            "Concise Summary URL"
        ]
        
        print("\nReport columns:", ", ".join(headers))
        print(f"\nTotal rows in report: {len(df)}")
        
        # Check if insight columns exist
        for column in insight_columns:
            if column in df.columns:
                non_empty = df[column].notna() & (df[column] != "") & (df[column] != "N/A")
                count = non_empty.sum()
                print(f"\n{column}:")
                print(f"  - Column exists: Yes")
                print(f"  - Non-empty values: {count} out of {len(df)} ({count/len(df)*100:.1f}% if df is not empty)")
                
                # Show sample URLs if available
                if count > 0:
                    sample_urls = df[df[column].notna() & (df[column] != "") & (df[column] != "N/A")][column].head(3).tolist()
                    print(f"  - Sample URLs:")
                    for url in sample_urls:
                        print(f"    * {url}")
            else:
                print(f"\n{column}:")
                print(f"  - Column exists: No")
        
    except Exception as e:
        print(f"Error accessing the Zoom Report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 