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

AI-Powered Viral Clip Generator & Dead-Air Remover — Upload a video or paste a YouTube link, get ranked viral clips automatically.

## How It Works

1. **Input**: Upload a video file (MP4, MOV, AVI, MKV, WEBM) **or paste a YouTube video / Shorts link**.
2. **Audio Transcription**: `faster-whisper` transcribes spoken words with timestamps on your local machine (100% free).
3. **Dead-Air Detection**: FFmpeg detects silent pauses and dead air throughout the video.
4. **AI Virality Analysis**: Google Gemini 2.0 Flash (or built-in local smart heuristic analyzer) analyzes hooks, pacing, and emotional peaks to pinpoint the best 10–20s moments.
5. **Precision Dead-Air Splicing**: FFmpeg cuts the clips and splices out internal pauses (>0.8s) for punchy, high-retention short clips.
6. **Ranked Clips Preview**: Watch the clips in-browser, copy captions/hashtags in 1-click, and download MP4 files ready for TikTok, Instagram Reels, and YouTube Shorts.

## Tech Stack (100% Free)

| Component | Tool | Cost |
|---|---|---|
| Backend | Python FastAPI | Free |
| YouTube Downloader | `yt-dlp` | Free |
| Transcription | `faster-whisper` (runs locally) | Free |
| AI Analysis | Google Gemini 2.0 Flash (Free API) or Local Smart Cadence Engine | Free |
| Video Processing | FFmpeg (`silencedetect` + `concat`) | Free |
| Frontend | HTML5 + Tailwind CSS + Vanilla JS | Free |

## Quick Start (Windows)

Just double-click:
```
run.bat
```
This automatically sets up the environment and opens `http://localhost:8000` in your browser.

## Manual Start

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Then visit `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/youtube` | Download and prepare a YouTube video |
| POST | `/api/upload` | Upload a local video file |
| POST | `/api/process/{job_id}` | Start processing pipeline |
| GET | `/api/status/{job_id}` | Check job progress |
| GET | `/api/results/{job_id}` | Retrieve ranked viral clips metadata |
| GET | `/api/clips/{job_id}/{filename}` | Download generated clip video |
| GET | `/api/health` | Health & API key check |
| DELETE | `/api/job/{job_id}` | Clean up job files |

## License

MIT — Free to use, modify, and distribute.
