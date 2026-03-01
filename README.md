# TenderApp

Intelligent Tender Tracking & Management Application

## Features

- **Tender Discovery** — Monitor RSS feeds and websites for new tenders automatically
- **Smart Notifications** — Get alerted on new tenders and upcoming deadlines
- **AI Document Writing** — Generate proposals, cover letters, methodology sections using Claude AI
- **Document Upload & Analysis** — Upload tender specs (PDF, DOCX, TXT) and let AI extract key info
- **Submission Pipeline** — Track bids from Draft → Review → Submitted → Won/Lost
- **Full CRUD** — Add, edit, delete tenders with rich metadata

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here

# 3. Run the app
python run.py
```

Open http://localhost:5000 in your browser.

## Project Structure

```
TenderApp/
├── app.py                  # Flask app factory + scheduler
├── run.py                  # Entry point
├── requirements.txt
├── backend/
│   ├── database.py         # SQLAlchemy setup
│   ├── models.py           # DB models: Tender, Document, Submission, Source, Notification
│   ├── routes/
│   │   ├── tenders.py      # CRUD + stats
│   │   ├── documents.py    # Upload + download + CRUD
│   │   ├── submissions.py  # Pipeline management
│   │   ├── ai.py           # AI chat, write, analyze endpoints
│   │   ├── sources.py      # Monitor sources
│   │   └── notifications.py
│   └── services/
│       ├── ai_service.py   # Claude API integration
│       ├── tender_monitor.py # RSS/web scraping
│       └── document_service.py # File handling, DOCX/PDF export
└── frontend/
    ├── index.html          # Single-page app
    ├── style.css           # Full UI styles
    └── app.js              # Frontend logic
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Claude API key for AI features |
| `SECRET_KEY` | dev key | Flask secret key |
| `DATABASE_URL` | sqlite:///tenderapp.db | Database connection |
| `UPLOAD_FOLDER` | uploads/ | File upload directory |
| `MAX_CONTENT_LENGTH` | 16MB | Max upload size |

## AI Features

All AI features use Claude (claude-opus-4-6 for quality, claude-haiku-4-5 for speed):

- **Extract tender from text** — Paste any tender notice and AI extracts all fields
- **Generate AI analysis** — Get a business-oriented summary of any tender
- **AI Writer chat** — Full conversation interface for writing tender documents
- **Document types**: Bid Proposal, Cover Letter, Executive Summary, Methodology, Company Profile, Financial Proposal, Compliance Statement
- **Improve documents** — Edit existing documents with AI instructions
- **Upload & analyze** — Upload PDFs/DOCX and AI extracts tender requirements

## Tender Sources

Configure RSS feeds or websites to monitor automatically. The background scheduler checks every 1 hour and creates notifications for new tenders.

Popular tender RSS feeds to try:
- UN Global Marketplace: https://www.ungm.org/Public/Notice/Feed
- World Bank: https://projects.worldbank.org/en/projects-operations/procurement/rss
