import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import routers
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router
import config

app = FastAPI(
    title="Zoom Transcript Insights",
    description="Automated insights extraction from Zoom recording transcripts",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse, tags=["ui"])
async def index(request: Request):
    """Serve the main HTML interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.DEBUG,
    )
