#!/usr/bin/env python3
"""
Script to check which entries have insight URLs in the Zoom Report.
"""

import os
import sys
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import config

def main():
    """Check which entries have insight URLs in the Zoom Report."""
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
        
        print(f"\nTotal rows in report: {len(df)}")
        
        # Find entries with insight URLs
        has_insights = df[insight_columns[0]].notna() & (df[insight_columns[0]] != "") & (df[insight_columns[0]] != "N/A")
        entries_with_insights = df[has_insights]
        
        print(f"\nFound {len(entries_with_insights)} entries with insight URLs:")
        
        # Print details of entries with insights
        if len(entries_with_insights) > 0:
            print("\nEntries with insight URLs:")
            for i, row in entries_with_insights.iterrows():
                topic = row.get("Meeting Topic", f"Row {i}")
                date = row.get("Date", "Unknown date")
                print(f"{i+1}. {topic} ({date})")
                
                # Check if all insight URLs are present
                missing = []
                for col in insight_columns:
                    if col not in row or pd.isna(row[col]) or row[col] == "" or row[col] == "N/A":
                        missing.append(col)
                
                if missing:
                    print(f"   Missing: {', '.join(missing)}")
                else:
                    print("   All insight URLs present")
        
        # Find entries without insight URLs
        entries_without_insights = df[~has_insights]
        print(f"\nFound {len(entries_without_insights)} entries without insight URLs")
        
        if len(entries_without_insights) > 0:
            print("\nSample of entries without insight URLs:")
            for i, row in entries_without_insights.head(5).iterrows():
                topic = row.get("Meeting Topic", f"Row {i}")
                date = row.get("Date", "Unknown date")
                print(f"- {topic} ({date})")
        
    except Exception as e:
        print(f"Error accessing the Zoom Report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 