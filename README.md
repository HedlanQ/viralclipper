---
title: ViralClipper
emoji: ⚡
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
app_port: 7860
pinned: false
---

# ⚡ ViralClipper

AI-Powered Raw Viral Short-Clip Generator — Upload a long video (up to 2 GB) and automatically extract ranked, sentence-complete 20–40s viral clips ready for TikTok, Instagram Reels, and YouTube Shorts.

## Key Features

1. **Up to 2 GB Video Uploads**: Streams large video files (`MP4`, `MOV`, `AVI`, `MKV`, `WEBM`) in 1 MB disk chunks for low-memory cloud hosting. *(YouTube Link tab is currently marked Coming Soon).*
2. **Groq Cloud Whisper-Large-V3-Turbo + Local Fallback**:
   - **Cloud LPU Mode**: Instant audio stream-copy with automatic 10-minute chunking for long videos, transcribing via Groq `whisper-large-v3-turbo` in seconds with anti-hallucination filtering.
   - **Local Mode**: Falls back to `faster-whisper` when running offline without a cloud key.
3. **Narrative & Lesson-Aware AI Virality Analyzer**:
   - Uses **Google Gemini 2.0 Flash** (or the built-in **Narrative & Lesson-Aware Local Engine**) to score hooks, explanations, and takeaways.
   - Snaps every clip to complete sentence boundaries with natural lead-in and tail audio buffers so sentences are never cut off.
4. **Keyframe-Locked Stream Copy (~0.6s/clip)**:
   - Cuts clips at keyframe boundaries using `-noaccurate_seek` and `-copyts -to` for zero video re-encoding and frame-accurate audio sync, with optional dead-air removal.
5. **OLED Bento Studio UI & Workflow Tools**:
   - Watch ranked clips in-browser with exact saved filenames (`clip_01_score95.mp4`).
   - **1-Click Copy Clip Transcript**, **Copy Full Transcript**, and **Select Clips Checkbox Batch Download**.
   - **Private Browser History Drawer** to revisit past jobs, copy transcripts/captions, and reopen clip views anytime.

## Tech Stack

| Component | Technology | Cost |
|---|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn | Free |
| Cloud Transcription | Groq Cloud (`whisper-large-v3-turbo`) | Free Tier |
| Local Transcription | `faster-whisper` | Free |
| Virality & Lesson Analysis | Google Gemini 2.0 Flash or Built-in Narrative Heuristic Engine | Free |
| Video & Audio Processing | FFmpeg (Keyframe stream-copy + `silencedetect`) | Free |
| Frontend | HTML5 + Tailwind CSS + Vanilla JS (OLED Bento Studio UI) | Free |
| Cloud Deployment | Docker + Render (`render.yaml`) | Free Tier |

## Quick Start (Windows)

Double-click:
```bat
run.bat
```
This sets up the virtual environment and opens `http://localhost:8000` in your browser.

## Manual Start

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Then open `http://localhost:8000`.

## Environment Variables (`backend/.env`)

```env
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here_or_leave_blank_for_local_engine
WHISPER_MODEL=base
TARGET_CLIP_DURATION_MIN=20
TARGET_CLIP_DURATION_MAX=40
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Chunked upload for local video files (up to 2 GB) |
| POST | `/api/youtube` | Download and prepare a YouTube video |
| POST | `/api/process/{job_id}` | Start transcription, analysis, and clip-cutting pipeline |
| GET | `/api/status/{job_id}` | Poll live job progress percentage and stage |
| GET | `/api/results/{job_id}` | Retrieve ranked viral clips and full transcript |
| GET | `/api/clips/{job_id}/{filename}` | Stream or download generated `.mp4` clip |
| GET | `/api/health` | Health & active AI engine check |
| DELETE | `/api/job/{job_id}` | Clean up job files |

## License

MIT — Free to use, modify, and distribute.
