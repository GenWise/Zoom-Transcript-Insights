# Setting Up a Shared Drive for Zoom Recordings

This guide explains how to set up a shared drive in Google Workspace to store Zoom recordings and avoid the "Service Accounts do not have storage quota" error.

## Why Use a Shared Drive?

Google Service Accounts (which this application uses to access Google Drive) don't have their own storage quota. When you try to upload files using a service account to a regular folder in "My Drive", you'll encounter this error:

```
Service Accounts do not have storage quota. Leverage shared drives (https://developers.google.com/workspace/drive/api/guides/about-shareddrives), or use OAuth delegation (http://support.google.com/a/answer/7281227) instead.
```

Using a shared drive solves this problem because shared drives have their own storage allocation that service accounts can use.

## Step 1: Create a Shared Drive

1. Go to [Google Drive](https://drive.google.com)
2. In the left sidebar, click on "Shared drives"
3. Click the "+ New" button to create a new shared drive
4. Name your shared drive (e.g., "Zoom Recordings")
5. Click "Create"

## Step 2: Share the Drive with Your Service Account

1. Open your newly created shared drive
2. Click on the name of the shared drive at the top to open the settings
3. Click on "Manage members"
4. Click the "+ Add members" button
5. Enter the email address of your service account (found in your service account JSON file under `client_email`)
6. Set the permission to "Content manager"
7. Click "Send" (no email will actually be sent)

## Step 3: Get the Shared Drive ID

1. Navigate to your shared drive in Google Drive
2. Look at the URL in your browser's address bar
3. The URL will look something like: `https://drive.google.com/drive/u/0/folders/0ABCdefGHIjklMNopqrsTUVwxyz`
4. The part after `folders/` is your shared drive ID (in this example: `0ABCdefGHIjklMNopqrsTUVwxyz`)

## Step 4: Update Your .env File

1. Open your `.env` file
2. Find the `GOOGLE_SHARED_DRIVE_ID` variable
3. Set its value to the shared drive ID you copied:
   ```
   GOOGLE_SHARED_DRIVE_ID='0ABCdefGHIjklMNopqrsTUVwxyz'
   ```
4. Save the file

## Step 5: Create a Root Folder (Optional)

If you want to organize your recordings within the shared drive:

1. Open your shared drive
2. Create a new folder (e.g., "Zoom Recordings")
3. Get the ID of this folder from the URL when you open it
4. Update the `GOOGLE_DRIVE_ROOT_FOLDER` in your `.env` file with this ID

## Troubleshooting

- If you still encounter permission issues, make sure your service account has "Content manager" permissions on the shared drive
- Verify that the shared drive ID is correctly copied into your `.env` file
- Check that your application has been updated to use the shared drive ID (the code changes should handle this automatically)

## Additional Resources

- [Google Drive API - Working with Shared Drives](https://developers.google.com/drive/api/guides/about-shareddrives)
- [Google Workspace Admin Help - Shared Drives](https://support.google.com/a/topic/7337266) 