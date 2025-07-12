#!/usr/bin/env python3
"""
Script to check if insight URLs are present for recently processed sessions.
"""

import os
import sys
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import config
from datetime import datetime, timedelta

def main():
    """Check the Zoom Report for recently added insight URLs."""
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
        
        print("\nTotal rows in report:", len(df))
        
        # Sort by most recent first if Date column exists
        if "Date" in df.columns:
            try:
                # Try to convert dates to datetime for sorting
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.sort_values(by="Date", ascending=False)
                print("Sorted by date (most recent first)")
            except Exception as e:
                print(f"Could not sort by date: {e}")
        
        # Look at the most recent 12 entries
        recent_df = df.head(12)
        print(f"\nAnalyzing the 12 most recent entries:")
        
        # Print meeting topics of the recent entries
        if "Meeting Topic" in recent_df.columns:
            print("\nRecent meeting topics:")
            for i, topic in enumerate(recent_df["Meeting Topic"].tolist()):
                print(f"{i+1}. {topic}")
        
        # Check insight URLs for recent entries
        print("\nInsight URL status for recent entries:")
        
        # Count URLs for each insight type
        url_counts = {}
        for column in insight_columns:
            if column in recent_df.columns:
                non_empty = recent_df[column].notna() & (recent_df[column] != "") & (recent_df[column] != "N/A")
                url_counts[column] = non_empty.sum()
        
        # Print summary
        print("\nURL counts for the 12 most recent entries:")
        for column, count in url_counts.items():
            print(f"- {column}: {count}/12 ({count/12*100:.1f}%)")
        
        # Check if all URLs are present for all recent entries
        all_complete = True
        for i, row in recent_df.iterrows():
            missing_urls = []
            for column in insight_columns:
                if column in row and (pd.isna(row[column]) or row[column] == "" or row[column] == "N/A"):
                    missing_urls.append(column)
            
            if missing_urls:
                all_complete = False
                print(f"\nEntry '{row.get('Meeting Topic', f'Row {i}')}' is missing: {', '.join(missing_urls)}")
        
        if all_complete:
            print("\nAll 12 recent entries have complete insight URLs!")
        else:
            print("\nSome recent entries are missing insight URLs.")
        
    except Exception as e:
        print(f"Error accessing the Zoom Report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 