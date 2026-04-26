# Workify

> Apply smarter. Not harder.

LLM-powered automated job application platform. Search LinkedIn jobs, generate tailored resumes and cover letters with AI, and submit applications automatically.

## Tech Stack

**Frontend:** React 18 + Vite + JavaScript + Tailwind CSS + Framer Motion  
**Backend:** FastAPI + Beanie (MongoDB ODM) + Groq LLM + browser-use  
**Auth:** Firebase (Google OAuth + Email/Password)  
**Database:** MongoDB Atlas  
**Storage:** Cloudinary (PDFs + resume files)  
**Deployment:** Vercel (frontend) + Render (backend)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- MongoDB Atlas account (free M0 tier)
- Firebase project (with Auth enabled)
- Groq API key
- Cloudinary account (free tier)

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env   # Edit with your Firebase config
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate     # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
playwright install chromium
cp ../.env.example .env    # Edit with all backend config
uvicorn app:app --reload --port 8080
```

## Project Structure

```
workify/
├── frontend/          React + Vite + Tailwind
│   ├── src/
│   │   ├── components/    Layout, JobCard, StatusPill, etc.
│   │   ├── pages/         Landing, Login, Dashboard, etc.
│   │   ├── lib/           API client, React Query, SSE hook
│   │   ├── store/         Zustand stores (auth, settings)
│   │   └── types/         JSDoc type definitions
│   └── ...config files
├── backend/           FastAPI + Beanie + Groq
│   ├── core/          Config, security, dependencies
│   ├── models/        Beanie document models
│   ├── routers/       API endpoints
│   ├── services/      Business logic
│   ├── prompts/       LLM system prompts
│   └── utils/         Helpers
└── spec.md            Full build specification
```

## Features

- LinkedIn job scraping via browser-use (LLM-driven)
- AI-generated tailored resumes, cover letters, and Q&A
- Automated application submission
- PDF export via WeasyPrint + Cloudinary storage
- Profile builder + PDF resume import (LLM-parsed)
- Application pipeline tracker (Kanban + Table)
- SSE-based live log streaming
- Firebase Auth (Google OAuth + Email/Password)
- Encrypted LinkedIn credential storage (Fernet AES-128)
- Rate limiting + concurrency caps

## Deployment

- **Frontend:** Deploy to Vercel with `vercel.json` config
- **Backend:** Deploy to Render with `render.yaml` config
- See `spec.md` for detailed deployment instructions

## License

MIT
