"""Pydantic models for request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class JobStatus(BaseModel):
    """Represents the current status of a processing job."""

    job_id: str
    status: str  # uploaded, transcribing, analyzing, cutting, done, error
    progress: int = 0  # 0-100
    step_description: str = ""
    error_message: Optional[str] = None


class ClipInfo(BaseModel):
    """Information about a single generated clip."""

    rank: int
    virality_score: int  # 1-100
    title: str
    description: str
    transcript: str = ""
    viral_captions: list[str] = []
    best_caption: str = ""
    start_time: float
    end_time: float
    duration: float = 0.0
    reason: str
    filename: str = ""
    thumbnail_time: float = 0.0


class ProcessingResult(BaseModel):
    """Complete results from video processing."""

    job_id: str
    total_clips: int
    clips: list[ClipInfo]
    video_duration: float
    processing_time: float = 0.0
    transcript_text: Optional[str] = ""


class ProcessRequest(BaseModel):
    """Optional settings passed when triggering video processing."""

    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    target_duration_min: Optional[int] = None
    target_duration_max: Optional[int] = None
    remove_dead_air: Optional[bool] = True


class YouTubeRequest(BaseModel):
    """Request payload for processing a YouTube video URL."""

    url: str


class CaptionGenerateRequest(BaseModel):
    """Request payload to generate or refine viral captions for a clip."""

    transcript: str
    feedback: Optional[str] = None
    previous_captions: Optional[list[str]] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class CaptionGenerateResponse(BaseModel):
    """Response payload with 5-10 viral captions and the Best Pick."""

    captions: list[str]
    best_pick: str
