zoom-transcript-insights/
├── .env                     # Environment variables
├── requirements.txt         # Dependencies
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration settings
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API endpoints
│   │   └── webhook.py       # Zoom webhook handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── zoom_service.py  # Zoom API integration
│   │   ├── drive_service.py # Google Drive integration
│   │   ├── claude_service.py # Claude API integration
│   │   └── transcript_processor.py # VTT processing
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   └── utils/
│       ├── __init__.py
│       └── vtt_parser.py    # VTT parsing utilities
└── static/
    └── index.html           # Simple web interface
