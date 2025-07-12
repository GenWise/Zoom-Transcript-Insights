from fastapi import FastAPI
import sys
import os

# Add the current directory to the path so Python can find your modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import your actual FastAPI app
from main import app

# This file is used as the entry point for Vercel deployment
# Vercel expects a variable named 'app' that is the FastAPI application instance

# For debugging purposes
@app.get("/debug")
async def debug_info():
    """
    Debug endpoint to check if the application is running correctly.
    """
    return {
        "status": "ok",
        "message": "Application is running",
        "routes": [
            {"path": route.path, "name": route.name} 
            for route in app.routes
        ]
    } 