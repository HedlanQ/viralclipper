"""ViralClipper - AI-Powered Viral Clip Generator API."""

import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings, ensure_directories, get_groq_api_key
from app.models import (
    JobStatus,
    ClipInfo,
    ProcessingResult,
    ProcessRequest,
    YouTubeRequest,
    CaptionGenerateRequest,
    CaptionGenerateResponse,
    LoginRequest,
    RefillRequest,
)
from app.services.transcription import transcribe_video
from app.services.analyzer import analyze_transcript, extract_clip_transcript
from app.services.caption_generator import (
    generate_viral_captions,
    populate_clips_viral_captions,
)
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


# ─── Owner Auth & Credit System ───────────────────────────────────────────────
# shortcut: single-owner file-backed credit ledger, upgrade to DB when scaling multi-tenant accounts


def _get_auth_token() -> str:
    """Deterministic HMAC session token so container restarts never invalidate active login."""
    secret = f"vc-auth:{settings.ADMIN_USERNAME}:{settings.ADMIN_PASSWORD}".encode("utf-8")
    return hmac.new(secret, b"viralclipper-owner-session", hashlib.sha256).hexdigest()


def _load_credit_state() -> dict:
    """Load persisted credit balance or initialize with INITIAL_CREDITS."""
    if os.path.exists(settings.AUTH_STATE_FILE):
        try:
            with open(settings.AUTH_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "credits": int(data.get("credits", settings.INITIAL_CREDITS)),
                    "used_credits": int(data.get("used_credits", 0)),
                }
        except Exception:
            pass
    return {"credits": settings.INITIAL_CREDITS, "used_credits": 0}


def _save_credit_state(state: dict) -> None:
    """Persist credit balance to disk."""
    try:
        with open(settings.AUTH_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"Could not save credit state: {e}")


def _require_auth(request: Request) -> dict:
    """Validate Bearer token and return current credit state."""
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
    if not token or not hmac.compare_digest(token, _get_auth_token()):
        raise HTTPException(
            status_code=401,
            detail="Please log in to your ViralClipper Studio account first.",
        )
    return _load_credit_state()


def _deduct_credits_for_duration(duration_seconds: float) -> tuple[int, int]:
    """Deduct 1 credit per minute of source video (rounded up, min 1 credit)."""
    cost = max(1, int(math.ceil(max(duration_seconds, 1.0) / 60.0)))
    state = _load_credit_state()
    state["credits"] = max(0, state["credits"] - cost)
    state["used_credits"] = state.get("used_credits", 0) + cost
    _save_credit_state(state)
    return cost, state["credits"]


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
    groq_key = config.get("groq_api_key") or get_groq_api_key()
    min_dur = config.get("target_duration_min") or settings.TARGET_CLIP_DURATION_MIN
    max_dur = config.get("target_duration_max") or settings.TARGET_CLIP_DURATION_MAX
    remove_dead_air = config.get("remove_dead_air", True)

    try:
        # Step 1: Get video info
        update_status(job_id, "transcribing", 5, "Examining video track...")
        duration = await asyncio.to_thread(get_video_duration, video_path)
        job_data["video_duration"] = duration
        logger.info(f"Video duration: {duration:.1f}s")

        # Step 2: Skip full-file silence scan when Groq Cloud word timestamps are active (saves 45s on cloud CPU!)
        if groq_key:
            silence_segments = []
        else:
            update_status(job_id, "transcribing", 12, "Detecting dead air and pauses...")
            silence_segments = await asyncio.to_thread(detect_silence, video_path)
            logger.info(f"Found {len(silence_segments)} silence segments")

        # Step 3: Transcribe
        whisper_desc = (
            "Extracting audio & transcribing via Groq Cloud..."
            if groq_key
            else "Transcribing audio with Whisper AI..."
        )
        update_status(job_id, "transcribing", 25, whisper_desc)

        def on_transcribe_progress(chunk_idx: int, total_chunks: int):
            if total_chunks > 1:
                pct = 25 + int(((chunk_idx - 1) / total_chunks) * 32)
                update_status(
                    job_id,
                    "transcribing",
                    min(58, pct),
                    f"Transcribing audio part {chunk_idx} of {total_chunks} via Groq Cloud...",
                )

        transcript = await asyncio.to_thread(
            transcribe_video, video_path, groq_key, on_transcribe_progress
        )
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
            words=transcript.get("words"),
        )
        update_status(
            job_id, "analyzing", 80, f"Found {len(clips)} high-potential viral moments!"
        )

        if not clips:
            raise RuntimeError("Could not identify viral moments. Try adjusting clip duration.")

        # Step 5: Cut clips with live per-clip progress updates (85% -> 95%)
        total_clips_to_cut = len(clips)
        update_status(
            job_id,
            "cutting",
            85,
            f"Cutting clip 1 of {total_clips_to_cut}...",
        )

        def on_clip_progress(done_count: int, total_count: int):
            pct = 85 + int((done_count / max(1, total_count)) * 10)
            if done_count < total_count:
                desc = f"Cut {done_count}/{total_count} clips • Cutting clip {done_count + 1} of {total_count}..."
            else:
                desc = f"All {total_count}/{total_count} clips cut! Finalizing MP4 files..."
            update_status(job_id, "cutting", min(95, pct), desc)

        filenames = await asyncio.to_thread(
            cut_clips,
            video_path,
            clips,
            job_output_dir,
            silence_segments=silence_segments,
            remove_dead_air=remove_dead_air,
            progress_callback=on_clip_progress,
        )

        # Re-sync each clip's exact spoken transcript to its final cut window
        # (since keyframe-locked stream copy adjusts clip.start_time to the exact I-frame)
        for clip in clips:
            synced = extract_clip_transcript(
                transcript["segments"],
                clip.start_time,
                clip.end_time,
                words=transcript.get("words"),
            )
            if synced:
                clip.transcript = synced
                if not api_key:
                    clip.description = synced

        update_status(job_id, "cutting", 96, "Generating viral in-video captions...")
        await asyncio.to_thread(
            populate_clips_viral_captions,
            clips,
            groq_api_key=groq_key,
            gemini_api_key=api_key,
        )

        # Free disk/RAM space by removing the large source upload once clips are cut
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.info(f"Cleaned up source upload {video_path} to free cloud memory.")
            except Exception:
                pass

        # Step 6: Deduct credits (1 credit = 1 min of source video, rounded up, only on success)
        cost, remaining_credits = _deduct_credits_for_duration(duration)
        elapsed = time.time() - start_time
        full_transcript = transcript.get("full_text", "")
        job_data["result"] = ProcessingResult(
            job_id=job_id,
            total_clips=len(clips),
            clips=clips,
            video_duration=duration,
            processing_time=round(elapsed, 1),
            transcript_text=full_transcript,
            credits_deducted=cost,
            credits_remaining=remaining_credits,
        )
        update_status(
            job_id,
            "done",
            100,
            f"All {len(clips)} clips ready! (-{cost} credit{'s' if cost != 1 else ''}, {remaining_credits} left)",
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
        "has_groq_key": bool(get_groq_api_key()),
        "yt_engine_version": "3-engine-clipto-pytubefix-ytdlp",
    }


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """Authenticate owner account and return session token + credit balance."""
    valid_user = req.username.strip().lower() == settings.ADMIN_USERNAME.strip().lower()
    valid_pass = hmac.compare_digest(req.password, settings.ADMIN_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    state = _load_credit_state()
    return {
        "token": _get_auth_token(),
        "username": settings.ADMIN_USERNAME,
        "credits": state["credits"],
        "used_credits": state["used_credits"],
    }


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Return current authenticated user profile and credit balance."""
    state = _require_auth(request)
    return {
        "username": settings.ADMIN_USERNAME,
        "credits": state["credits"],
        "used_credits": state["used_credits"],
    }


@app.post("/api/auth/refill")
async def auth_refill(request: Request, req: Optional[RefillRequest] = None):
    """Refill credits for testing."""
    state = _require_auth(request)
    add_amount = req.amount if (req and req.amount > 0) else 100
    state["credits"] += add_amount
    _save_credit_state(state)
    return {
        "username": settings.ADMIN_USERNAME,
        "credits": state["credits"],
        "used_credits": state["used_credits"],
        "added": add_amount,
    }


@app.post("/api/upload")
async def upload_video(request: Request, file: UploadFile = File(...)):
    """Upload a video file for processing (requires login and positive credits)."""
    state = _require_auth(request)
    if state["credits"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits (0 remaining). Click '+ Refill' in the navbar to top up.",
        )

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
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB streaming chunks (prevents RAM crash on large 1GB-2GB uploads)
        with open(save_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE:
                    f.close()
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size is {format_file_size(settings.MAX_FILE_SIZE)}.",
                    )
                f.write(chunk)

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


@app.api_route("/api/clips/{job_id}/{clip_filename}", methods=["GET", "HEAD"])
async def serve_clip(request: Request, job_id: str, clip_filename: str, download: bool = False):
    """Serve a generated clip video file with HTTP Range (206 Partial Content) support for smooth seeking."""
    safe_job_id = os.path.basename(job_id)
    safe_filename = os.path.basename(clip_filename)
    clip_path = os.path.join(settings.OUTPUT_DIR, safe_job_id, safe_filename)
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip file not found")

    file_size = os.path.getsize(clip_path)
    disposition = "attachment" if download else "inline"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
    }

    range_header = request.headers.get("range")
    if range_header:
        match = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
        if match:
            start_str, end_str = match.groups()
            if start_str and end_str:
                start = int(start_str)
                end = min(int(end_str), file_size - 1)
            elif start_str:
                start = int(start_str)
                end = file_size - 1
            elif end_str:
                start = max(0, file_size - int(end_str))
                end = file_size - 1
            else:
                start, end = 0, file_size - 1

            if start >= file_size or start > end or start < 0:
                return Response(
                    status_code=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            chunk_length = end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(chunk_length)

            if request.method.upper() == "HEAD":
                return Response(status_code=206, media_type="video/mp4", headers=headers)

            def iter_range():
                with open(clip_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_length
                    while remaining > 0:
                        data = f.read(min(65536, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            return StreamingResponse(
                iter_range(),
                status_code=206,
                media_type="video/mp4",
                headers=headers,
            )

    headers["Content-Length"] = str(file_size)
    if request.method.upper() == "HEAD":
        return Response(status_code=200, media_type="video/mp4", headers=headers)

    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers=headers,
    )


@app.post("/api/captions/generate", response_model=CaptionGenerateResponse)
async def api_generate_captions(req: CaptionGenerateRequest):
    """Generate or refine 5-10 viral in-video captions + Best Pick for a clip transcript."""
    if not req.transcript or not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Clip transcript is required.")

    groq_key = req.groq_api_key or get_groq_api_key()
    gemini_key = req.gemini_api_key or settings.GEMINI_API_KEY

    result = await asyncio.to_thread(
        generate_viral_captions,
        req.transcript.strip(),
        feedback=req.feedback,
        previous_captions=req.previous_captions,
        groq_api_key=groq_key,
        gemini_api_key=gemini_key,
    )
    return CaptionGenerateResponse(
        captions=result.get("captions", []),
        best_pick=result.get("best_pick", ""),
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
