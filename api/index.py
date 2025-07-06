from fastapi import FastAPI
import sys
import os

# Add the parent directory to the path so Python can find your modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your actual FastAPI app
from main import app

# This is required for Vercel serverless functions
# Vercel will look for a handler function
def handler(request, context):
    return app(request, context) 