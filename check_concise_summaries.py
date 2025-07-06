#!/usr/bin/env python
"""
Script to check for concise summary files in Google Drive.
"""

import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    # Get credentials
    credentials_file = "sheets-and-python-340711-0c9221224a70.json"
    scopes = ["https://www.googleapis.com/auth/drive"]
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        
        # Build the Drive service
        service = build("drive", "v3", credentials=credentials)
        
        # Search for concise summary files
        results = service.files().list(
            q="name = 'concise_summary.md' and trashed = false",
            fields="files(id, name, webViewLink, parents)"
        ).execute()
        
        files = results.get("files", [])
        print(f"Found {len(files)} concise summary files:")
        
        for file in files:
            # Get parent folder name
            parent_id = file.get("parents", [""])[0]
            parent_info = service.files().get(fileId=parent_id, fields="name").execute()
            parent_name = parent_info.get("name", "Unknown folder")
            
            print(f"- {parent_name}: {file.get('webViewLink', 'No link')}")
            
        # Also check for executive summary files for comparison
        exec_results = service.files().list(
            q="name = 'executive_summary.md' and trashed = false",
            fields="files(id, name, webViewLink, parents)"
        ).execute()
        
        exec_files = exec_results.get("files", [])
        print(f"\nFound {len(exec_files)} executive summary files for comparison")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 