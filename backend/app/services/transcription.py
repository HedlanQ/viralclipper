"""
Transcription service supporting:
1. Groq Cloud Whisper API ('whisper-large-v3-turbo') - 20x faster, highest accuracy, zero local CPU/RAM!
2. Local faster-whisper fallback (with word-level timestamp alignment and caching).
"""

import hashlib
import json
import logging
import os
import subprocess
import urllib.request
import urllib.error
import uuid
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Global local model instance (lazy-loaded only if Groq Cloud API is not used)
_model = None


def _get_model():
    """Lazy-load the local faster-whisper model only when needed."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        cpu_threads = min(8, max(2, os.cpu_count() or 4))
        logger.info(
            f"Loading local Whisper model '{settings.WHISPER_MODEL}' (CPU threads: {cpu_threads})..."
        )
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
        )
        logger.info("Local Whisper model loaded successfully.")
    return _model


def _get_cache_path(video_path: str, engine_tag: str) -> str:
    """Generate a cache path based on file size, mtime, and transcription engine."""
    try:
        stat = os.stat(video_path)
        key = f"v3_words_{engine_tag}_{os.path.basename(video_path)}_{stat.st_size}_{int(stat.st_mtime)}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        return os.path.join(settings.TEMP_DIR, f"transcript_{digest}.json")
    except Exception:
        return ""


def _extract_audio_for_transcription(video_path: str, for_cloud: bool = False) -> str:
    """
    Extract a compact mono audio file for speech recognition.
    For Groq Cloud API, uses 16kHz 48kbps M4A (<4MB for 15 mins) so upload is sub-second
    and always stays well under the 25MB API limit.
    """
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    if for_cloud:
        temp_audio = os.path.join(settings.TEMP_DIR, f"audio_{uuid.uuid4().hex[:8]}.m4a")
        cmd = [
            "ffmpeg",
            "-y",
            "-nostats",
            "-vn",
            "-sn",
            "-dn",
            "-i", video_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "aac",
            "-b:a", "24k",
            temp_audio,
        ]
    else:
        temp_audio = os.path.join(settings.TEMP_DIR, f"audio_{uuid.uuid4().hex[:8]}.wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-nostats",
            "-vn",
            "-sn",
            "-dn",
            "-i", video_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            temp_audio,
        ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode == 0 and os.path.exists(temp_audio):
        return temp_audio
    logger.warning("Fast audio extraction failed, falling back to direct video path.")
    return video_path


def _transcribe_via_groq_cloud(audio_path: str, groq_api_key: str) -> dict:
    """
    Transcribe audio in 2-3 seconds using Groq Cloud's Whisper-Large-V3-Turbo API
    with exact segment and word-level timestamps.
    """
    logger.info("Transcribing via Groq Cloud LPU ('whisper-large-v3-turbo')...")
    boundary = f"----ViralClipperBoundary{uuid.uuid4().hex}"
    url = "https://api.groq.com/openai/v1/audio/transcriptions"

    filename = os.path.basename(audio_path)
    with open(audio_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()

    def add_field(name: str, value: str):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    add_field("model", "whisper-large-v3-turbo")
    add_field("response_format", "verbose_json")
    add_field("temperature", "0")
    add_field("timestamp_granularities[]", "segment")
    add_field("timestamp_granularities[]", "word")

    # Add audio file part
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8")
    )
    body.extend(b"Content-Type: audio/mp4\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {groq_api_key.strip()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ViralClipper/2.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Groq Cloud Whisper API error ({e.code}): {err_body}")

    raw_segments = data.get("segments", [])
    all_words = data.get("words", [])
    segments = []
    full_text_parts = []

    for seg in raw_segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        s_start = float(seg.get("start", 0.0))
        s_end = float(seg.get("end", s_start + 1.0))

        # Refine with exact word-level timestamps if available in this window
        seg_words = [
            w for w in all_words
            if float(w.get("start", 0.0)) >= s_start - 0.15
            and float(w.get("end", 0.0)) <= s_end + 0.25
        ]
        if seg_words:
            s_start = float(seg_words[0].get("start", s_start))
            s_end = float(seg_words[-1].get("end", s_end))

        segments.append({
            "start": round(s_start, 2),
            "end": round(s_end, 2),
            "text": text,
        })
        full_text_parts.append(text)

    result = {
        "full_text": " ".join(full_text_parts),
        "segments": segments,
        "language": data.get("language", "en"),
        "engine": "whisper-large-v3-turbo (Groq Cloud)",
    }
    logger.info(
        f"Groq Cloud Whisper-Large-V3-Turbo complete: {len(segments)} segments!"
    )
    return result


def transcribe_video(video_path: str, groq_api_key: Optional[str] = None) -> dict:
    """
    Transcribe a video file using Groq Cloud ('whisper-large-v3-turbo') when configured,
    or fall back to local faster-whisper with word-level timestamps.
    """
    effective_groq_key = (groq_api_key or settings.GROQ_API_KEY or "").strip()
    engine_tag = "groq_v3_turbo" if effective_groq_key else f"local_{settings.WHISPER_MODEL}"

    cache_path = _get_cache_path(video_path, engine_tag)
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info(
                f"Loaded cached word-aligned transcript [{engine_tag}] ({len(cached['segments'])} segments)!"
            )
            return cached
        except Exception:
            pass

    # 1. Try Groq Cloud Whisper-Large-V3-Turbo first (0% local CPU/RAM, 20x faster, highest accuracy)
    if effective_groq_key:
        audio_source = _extract_audio_for_transcription(video_path, for_cloud=True)
        is_temp = audio_source != video_path
        try:
            result = _transcribe_via_groq_cloud(audio_source, effective_groq_key)
            if cache_path:
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(result, f)
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.warning(f"Groq Cloud transcription failed ({e}), falling back to local Whisper...")
        finally:
            if is_temp and os.path.exists(audio_source):
                try:
                    os.remove(audio_source)
                except Exception:
                    pass

    # 2. Local faster-whisper fallback
    logger.info(f"Starting local word-aligned transcription for: {video_path}")
    try:
        model = _get_model()
    except ImportError:
        raise RuntimeError(
            "Cloud mode requires a free Groq API Key (console.groq.com/keys) in Settings -> Groq Whisper Key, "
            "because local faster-whisper is not installed on this lightweight cloud server."
        )

    audio_source = _extract_audio_for_transcription(video_path, for_cloud=False)
    is_temp = audio_source != video_path

    try:
        segments_iter, info = model.transcribe(
            audio_source,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=350,
                speech_pad_ms=250,
            ),
        )

        segments = []
        full_text_parts = []

        for segment in segments_iter:
            text = segment.text.strip()
            if not text:
                continue

            words = getattr(segment, "words", None)
            if words:
                seg_start = round(words[0].start, 2)
                seg_end = round(words[-1].end, 2)
            else:
                seg_start = round(segment.start, 2)
                seg_end = round(segment.end, 2)

            segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": text,
            })
            full_text_parts.append(text)

        result = {
            "full_text": " ".join(full_text_parts),
            "segments": segments,
            "language": info.language,
            "engine": f"faster-whisper ({settings.WHISPER_MODEL})",
        }

        if cache_path:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(result, f)
            except Exception:
                pass

        return result

    finally:
        if is_temp and os.path.exists(audio_source):
            try:
                os.remove(audio_source)
            except Exception:
                pass
