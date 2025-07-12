# Zoom Webhook Integration

This document describes how to set up and use the Zoom webhook integration for the Insights from Online Courses application.

## Overview

The webhook integration allows the application to receive real-time notifications from Zoom when certain events occur, such as:

- Recording completed
- Meeting deleted
- App deauthorized

When these events occur, Zoom sends an HTTP POST request to our webhook endpoints with information about the event.

## Setting Up Zoom Webhooks

To set up webhooks in your Zoom account:

1. Log in to the [Zoom Marketplace](https://marketplace.zoom.us/)
2. Navigate to "Develop" > "Build App"
3. Create a new OAuth app or select your existing app
4. In the app settings, go to the "Feature" section and enable "Event Subscriptions"
5. Add the following webhook endpoints:
   - `https://your-domain.com/webhook/recording-completed` for recording.completed events
   - `https://your-domain.com/webhook/meeting-deleted` for meeting.deleted events
   - `https://your-domain.com/webhook/deauthorization` for app.deauthorized events
6. For the verification token, generate a random string and set it as your `ZOOM_WEBHOOK_SECRET` environment variable
7. Save the settings

## Environment Variables

Make sure to set the following environment variables:

```bash
# Webhook secret (from Zoom app settings)
export ZOOM_WEBHOOK_SECRET="your_zoom_webhook_secret"
```

## Webhook Endpoints

### Recording Completed

This endpoint is called when a recording is completed in Zoom.

- **URL**: `/webhook/recording-completed`
- **Method**: `POST`
- **Event Type**: `recording.completed`
- **Description**: Processes the recording, downloads the transcript, generates analysis, and uploads results to Google Drive.

### Meeting Deleted

This endpoint is called when a meeting is deleted in Zoom.

- **URL**: `/webhook/meeting-deleted`
- **Method**: `POST`
- **Event Type**: `meeting.deleted`
- **Description**: Handles cleanup of resources associated with the deleted meeting.

### App Deauthorized

This endpoint is called when a user removes your app's access to their Zoom account.

- **URL**: `/webhook/deauthorization`
- **Method**: `POST`
- **Event Type**: `app.deauthorized`
- **Description**: Handles cleanup of resources associated with the deauthorized account.

### Health Check

This endpoint is used by Zoom to verify the webhook is working.

- **URL**: `/webhook/health`
- **Method**: `GET`
- **Description**: Returns a simple status message to confirm the webhook is operational.

## Webhook Verification

All webhook requests from Zoom include a signature in the `x-zm-signature` header. The application verifies this signature to ensure the request is legitimate.

The signature is verified using the following steps:

1. Concatenate the timestamp and request body: `v0:{timestamp}:{request_body}`
2. Create an HMAC-SHA256 hash of this string using the webhook secret
3. Compare the resulting hash with the signature from Zoom

If the signatures don't match, the request is rejected with a 401 Unauthorized response.

## Testing Webhooks

For local development, you can use a service like [ngrok](https://ngrok.com/) to create a public URL that forwards to your local server:

```bash
ngrok http 8000
```

Then update your webhook URLs in the Zoom app settings to use the ngrok URL.

You can also use the test suite to verify the webhook functionality:

```bash
pytest tests/test_webhook.py
```

## Why Vercel vs. Local Implementation

### Why Vercel is Used

Vercel is used for webhook implementation for several reasons:

1. **Public URL Requirement**: Zoom webhooks require a publicly accessible URL to send notifications to. Vercel provides a stable, public-facing URL.

2. **SSL Support**: Zoom requires HTTPS endpoints for webhooks. Vercel automatically provides SSL certificates.

3. **Reliability**: Vercel offers high availability and reliability for webhook endpoints.

4. **Serverless Architecture**: Vercel's serverless functions are well-suited for webhook handlers that run infrequently but need to be always available.

### Local Implementation Alternative

You can implement webhooks locally without Vercel using the following approaches:

1. **Ngrok for Development**:
   - Install ngrok: `brew install ngrok` (Mac) or download from [ngrok.com](https://ngrok.com)
   - Run your FastAPI application locally: `uvicorn main:app --reload`
   - Create a tunnel with ngrok: `ngrok http 8000`
   - Use the ngrok URL (e.g., `https://a1b2c3d4.ngrok.io`) for your webhook endpoints in Zoom

2. **Self-hosted Server**:
   - Deploy the FastAPI application on your own server with a public IP
   - Set up SSL using Let's Encrypt or another certificate provider
   - Configure your server to run the application continuously (using systemd, supervisor, etc.)
   - Point your domain to the server and use it for webhook endpoints

3. **Scheduled Polling as Alternative**:
   - Instead of webhooks, you could implement a scheduled job that polls the Zoom API for new recordings
   - This approach doesn't require a public endpoint but may have higher latency and API usage
   - Use a cron job or scheduler to run scripts like `extract_historical_recordings.py` at regular intervals

### Implementation Choice

The choice between Vercel and local implementation depends on your specific needs:

- **Use Vercel** if you need a reliable, low-maintenance solution with minimal setup
- **Use local implementation** if you prefer to keep everything in-house or have specific security requirements

The current codebase supports both approaches - the webhook handlers in `app/api/webhook.py` can be used with either Vercel or a local server. 