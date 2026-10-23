"""ViralClipper - AI-Powered Viral Clip Generator API."""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings, ensure_directories
from app.models import JobStatus, ClipInfo, ProcessingResult, ProcessRequest, YouTubeRequest
from app.services.transcription import transcribe_video
from app.services.analyzer import analyze_transcript
from app.services.youtube_downloader import is_valid_youtube_url, download_youtube_video
from app.services.video_processor import (
    get_video_duration,
    detect_silence,
    cut_clips,
)
from app.utils.helpers import is_allowed_file, format_file_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory job storage
jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    ensure_directories()
    logger.info("ViralClipper API started successfully!")
    logger.info(f"Upload dir: {os.path.abspath(settings.UPLOAD_DIR)}")
    logger.info(f"Output dir: {os.path.abspath(settings.OUTPUT_DIR)}")
    if not settings.GEMINI_API_KEY:
        logger.info(
            "ℹ️  Note: GEMINI_API_KEY is not set in .env. "
            "You can enter it in the web UI settings or use the built-in local heuristic analyzer."
        )
    yield
    logger.info("ViralClipper API shutting down.")


app = FastAPI(
    title="ViralClipper API",
    description="AI-Powered Viral Clip Generator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def update_status(
    job_id: str, status: str, progress: int, description: str, error: str = None
):
    """Update the status of a job."""
    if job_id in jobs:
        jobs[job_id]["status"] = status
        jobs[job_id]["progress"] = progress
        jobs[job_id]["step_description"] = description
        if error:
            jobs[job_id]["error_message"] = error
        logger.info(f"Job {job_id}: [{status}] {progress}% - {description}")


async def process_video_pipeline(job_id: str):
    """
    Full video processing pipeline run as a background task.

    Steps:
        1. Get video duration
        2. Detect silence/dead air
        3. Transcribe with Whisper
        4. Analyze with AI (Gemini or local heuristic)
        5. Cut clips with FFmpeg (with dead-air excision)
    """
    start_time = time.time()
    job_data = jobs[job_id]
    video_path = job_data["video_path"]
    job_output_dir = os.path.join(settings.OUTPUT_DIR, job_id)
    config = job_data.get("config", {})

    api_key = config.get("gemini_api_key") or settings.GEMINI_API_KEY
    groq_key = config.get("groq_api_key") or settings.GROQ_API_KEY
    min_dur = config.get("target_duration_min") or settings.TARGET_CLIP_DURATION_MIN
    max_dur = config.get("target_duration_max") or settings.TARGET_CLIP_DURATION_MAX
    remove_dead_air = config.get("remove_dead_air", True)

    try:
        # Step 1: Get video info
        update_status(job_id, "transcribing", 5, "Examining video track...")
        duration = await asyncio.to_thread(get_video_duration, video_path)
        job_data["video_duration"] = duration
        logger.info(f"Video duration: {duration:.1f}s")

        # Step 2: Detect silence
        update_status(job_id, "transcribing", 12, "Detecting dead air and pauses...")
        silence_segments = await asyncio.to_thread(detect_silence, video_path)
        logger.info(f"Found {len(silence_segments)} silence segments")

        # Step 3: Transcribe
        whisper_desc = (
            "Transcribing in 3s via Groq Cloud (Whisper-Large-V3-Turbo)..."
            if groq_key
            else "Transcribing audio with Whisper AI..."
        )
        update_status(job_id, "transcribing", 25, whisper_desc)
        transcript = await asyncio.to_thread(transcribe_video, video_path, groq_key)
        update_status(job_id, "transcribing", 60, "Speech transcription complete!")

        if not transcript["segments"]:
            raise RuntimeError(
                "No speech was detected in this video. Please upload a video with audible speech."
            )

        # Step 4: Analyze with AI
        ai_desc = "Gemini AI" if api_key else "AI Content Analyzer"
        update_status(job_id, "analyzing", 68, f"{ai_desc} is identifying viral moments...")
        clips = await asyncio.to_thread(
            analyze_transcript,
            transcript["segments"],
            duration,
            silence_segments,
            api_key=api_key,
            min_duration=min_dur,
            max_duration=max_dur,
        )
        update_status(
            job_id, "analyzing", 80, f"Found {len(clips)} high-potential viral moments!"
        )

        if not clips:
            raise RuntimeError("Could not identify viral moments. Try adjusting clip duration.")

        # Step 5: Cut clips
        cutting_desc = (
            "Excising dead-air & cutting clips..."
            if remove_dead_air
            else "Cutting video clips with FFmpeg..."
        )
        update_status(job_id, "cutting", 85, cutting_desc)
        filenames = await asyncio.to_thread(
            cut_clips,
            video_path,
            clips,
            job_output_dir,
            silence_segments=silence_segments,
            remove_dead_air=remove_dead_air,
        )
        update_status(job_id, "cutting", 95, "Finalizing MP4 files...")

        # Step 6: Complete
        elapsed = time.time() - start_time
        job_data["result"] = ProcessingResult(
            job_id=job_id,
            total_clips=len(clips),
            clips=clips,
            video_duration=duration,
            processing_time=round(elapsed, 1),
        )
        update_status(
            job_id,
            "done",
            100,
            f"All {len(clips)} clips ready! Processed in {elapsed:.0f}s",
        )

    except Exception as e:
        logger.exception(f"Job {job_id} processing failed:")
        update_status(job_id, "error", 0, str(e), error=str(e))


# ─── API Endpoints ────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": "ViralClipper API",
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_groq_key": bool(settings.GROQ_API_KEY),
    }


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for processing."""
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Supported formats: MP4, MOV, AVI, MKV, WEBM",
        )

    job_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1].lower()
    save_filename = f"{job_id}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_filename)

    try:
        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {format_file_size(settings.MAX_FILE_SIZE)}.",
            )

        with open(save_path, "wb") as f:
            f.write(content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    jobs[job_id] = {
        "status": "uploaded",
        "progress": 0,
        "step_description": "Video uploaded successfully",
        "error_message": None,
        "video_path": save_path,
        "original_filename": file.filename,
        "file_size": file_size,
        "result": None,
        "config": {},
    }

    logger.info(
        f"Video uploaded: {file.filename} ({format_file_size(file_size)}) -> Job {job_id}"
    )

    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": file_size,
        "file_size_formatted": format_file_size(file_size),
    }


@app.post("/api/youtube")
async def process_youtube(req: YouTubeRequest):
    """
    Download a video from a YouTube URL and prepare it for viral clipping.
    """
    if not is_valid_youtube_url(req.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.",
        )

    job_id = str(uuid.uuid4())[:8]

    try:
        yt_info = await asyncio.to_thread(download_youtube_video, req.url, job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("YouTube download failed:")
        raise HTTPException(
            status_code=500, detail=f"Failed to download YouTube video: {str(e)}"
        )

    jobs[job_id] = {
        "status": "uploaded",
        "progress": 0,
        "step_description": f"Downloaded: {yt_info['title']}",
        "error_message": None,
        "video_path": yt_info["video_path"],
        "original_filename": f"{yt_info['title']}.mp4",
        "file_size": yt_info["file_size"],
        "video_duration": yt_info["duration"],
        "result": None,
        "config": {},
    }

    return {
        "job_id": job_id,
        "title": yt_info["title"],
        "duration": yt_info["duration"],
        "uploader": yt_info["uploader"],
        "file_size": yt_info["file_size"],
        "file_size_formatted": format_file_size(yt_info["file_size"]),
    }


@app.post("/api/process/{job_id}")
async def start_processing(
    job_id: str,
    background_tasks: BackgroundTasks,
    request: Optional[ProcessRequest] = None,
):
    """Start processing a previously uploaded video with optional custom settings."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if jobs[job_id]["status"] not in ("uploaded", "error"):
        raise HTTPException(
            status_code=400,
            detail=f"Job is already {jobs[job_id]['status']}",
        )

    # Store processing configuration if supplied
    jobs[job_id]["config"] = request.model_dump() if request else {}

    update_status(job_id, "transcribing", 0, "Initializing pipeline...")
    background_tasks.add_task(process_video_pipeline, job_id)

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the current processing status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        step_description=job["step_description"],
        error_message=job.get("error_message"),
    )


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """Get the processing results for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not done yet. Current status: {job['status']}",
        )

    if not job.get("result"):
        raise HTTPException(status_code=500, detail="Results not available")

    return job["result"]


@app.get("/api/clips/{job_id}/{clip_filename}")
async def serve_clip(job_id: str, clip_filename: str):
    """Serve a generated clip video file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    clip_path = os.path.join(settings.OUTPUT_DIR, job_id, clip_filename)
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip file not found")

    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=clip_filename,
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Clean up all files for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    import shutil

    video_path = jobs[job_id].get("video_path")
    if video_path and os.path.exists(video_path):
        os.remove(video_path)

    output_dir = os.path.join(settings.OUTPUT_DIR, job_id)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    del jobs[job_id]
    return {"status": "deleted", "job_id": job_id}


# ─── Serve Frontend UI ────────────────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
