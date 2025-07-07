# Alternatives to Vercel for Webhook Implementation

This document outlines alternatives to using Vercel for implementing Zoom webhooks in the Insights from Online Courses application.

## Understanding the Need for Webhooks

Zoom webhooks require a publicly accessible HTTPS endpoint that Zoom can send event notifications to. The main requirements are:

1. A public URL that's accessible from the internet
2. HTTPS/SSL support
3. Reliable uptime
4. Ability to run the FastAPI application

## Alternative 1: Ngrok for Development and Testing

[Ngrok](https://ngrok.com) is a great tool for development and testing webhooks locally.

### Setup Steps

1. **Install ngrok**:
   ```bash
   # macOS with Homebrew
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Run your FastAPI application locally**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

3. **Create a tunnel with ngrok**:
   ```bash
   ngrok http 8000
   ```

4. **Use the ngrok URL for webhook endpoints**:
   - Ngrok will provide a URL like `https://a1b2c3d4.ngrok.io`
   - Configure this URL in your Zoom app settings for webhook endpoints

### Pros and Cons

**Pros**:
- Free for basic usage
- Easy to set up and use
- Great for development and testing
- No need for Vercel account

**Cons**:
- URLs change each time you restart ngrok (unless you have a paid plan)
- Not suitable for production use (with free tier)
- Limited number of connections on free tier

## Alternative 2: Self-hosted Server with SSL

You can host the FastAPI application on your own server with a public IP address.

### Setup Steps

1. **Set up a server** with a cloud provider (AWS, DigitalOcean, Linode, etc.) or use an existing server

2. **Install required software**:
   ```bash
   # Update and install dependencies
   sudo apt update
   sudo apt install python3-pip python3-venv nginx

   # Clone your repository
   git clone https://github.com/your-username/Insights_from_Online_Courses.git
   cd Insights_from_Online_Courses
   
   # Set up virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up SSL with Let's Encrypt**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

4. **Configure Nginx as a reverse proxy**:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

5. **Run the FastAPI application with a production server**:
   ```bash
   # Install Gunicorn
   pip install gunicorn uvicorn

   # Create a systemd service file
   sudo nano /etc/systemd/system/insights.service
   ```

   Add the following content:
   ```
   [Unit]
   Description=Insights from Online Courses FastAPI Application
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/Insights_from_Online_Courses
   ExecStart=/home/ubuntu/Insights_from_Online_Courses/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start the service:
   ```bash
   sudo systemctl enable insights
   sudo systemctl start insights
   ```

### Pros and Cons

**Pros**:
- Complete control over your infrastructure
- No dependency on third-party services like Vercel
- No usage limits (other than your server capacity)
- Stable URL that doesn't change

**Cons**:
- More complex setup and maintenance
- Requires server administration knowledge
- Costs associated with running a server
- You're responsible for server uptime and security

## Alternative 3: Scheduled Polling Instead of Webhooks

If setting up a public endpoint is challenging, you can use scheduled polling instead of webhooks.

### Implementation Steps

1. **Create a cron job** to run the `extract_historical_recordings.py` script at regular intervals:
   ```bash
   # Edit crontab
   crontab -e
   
   # Add a line to run every hour
   0 * * * * cd /path/to/Insights_from_Online_Courses && python scripts/extract_historical_recordings.py --start-date $(date -d "1 day ago" +\%Y-\%m-\%d) --end-date $(date +\%Y-\%m-\%d)
   ```

2. **Adjust the script** to handle potential duplicate processing

### Pros and Cons

**Pros**:
- No need for public endpoints
- Works behind firewalls
- Simpler setup (no SSL, no public server)
- More control over when processing happens

**Cons**:
- Higher latency (recordings are processed on a schedule, not immediately)
- Increased API usage (polling regularly)
- May miss events if the polling interval is too long
- Less real-time than webhooks

## Recommendation

Based on your specific needs:

1. **For development and testing**: Use Ngrok
2. **For production with minimal setup**: Keep using Vercel
3. **For production with full control**: Use a self-hosted server
4. **For simplest implementation**: Use scheduled polling

The current codebase supports all these approaches with minimal changes. 