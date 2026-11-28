"""
Transcription service supporting:
1. Groq Cloud Whisper API ('whisper-large-v3' full accuracy, with 'whisper-large-v3-turbo' fallback)
   - Speech-cleaned audio extraction + hallucination filtering (no_speech_prob, avg_logprob, compression_ratio, repetition loops)
2. Local faster-whisper fallback (condition_on_previous_text=False, beam_size=5, word timestamps, VAD + hallucination filtering).
"""

import glob
import hashlib
import json
import logging
import os
import re
import subprocess
import urllib.request
import urllib.error
import uuid
from typing import Callable, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Global local model instance (lazy-loaded only if Groq Cloud API is not used)
_model = None

# Known Whisper silence/noise hallucination phrases (matched case-insensitively on normalized text)
KNOWN_HALLUCINATION_PHRASES = {
    "thank you",
    "thank you.",
    "thank you!",
    "thanks",
    "thanks.",
    "thank you for watching",
    "thank you for watching.",
    "thank you for watching!",
    "thanks for watching",
    "thanks for watching.",
    "thanks for watching!",
    "thank you so much for watching",
    "thank you so much for watching.",
    "please subscribe",
    "subscribe",
    "like and subscribe",
    "subtitles by",
    "transcribed by",
    "amara.org",
    "www.amara.org",
    "mbc news",
    "you",
    "you.",
    "bye",
    "bye.",
    "bye-bye",
    "bye bye",
    "music",
    "[music]",
    "(music)",
    "[applause]",
    "(applause)",
    "[laughter]",
    "(laughter)",
    "...",
    "…",
    "♪",
    "blah",
    "blah blah",
    "blah blah blah",
}

# Regex to catch babble/filler hallucination segments made almost entirely of "blah", "la", "uh", "hm", etc.
_BABBLE_ONLY_RE = re.compile(
    r"^(?:[\s,.\-!?]*(?:blah|bla|la|da|na|hm+|mm+|uh+|um+|ah+|oh+|ha|he|eh|shh?))+[\s,.\-!?]*$",
    re.IGNORECASE,
)

# Regex to detect consecutive repetition of any short 1-4 word phrase (4+ times in a row)
_REPETITION_LOOP_RE = re.compile(
    r"\b(\w+(?:\s+\w+){0,3})(?:[\s,]+(\1)){3,}\b",
    re.IGNORECASE,
)


def _normalize_text(text: str) -> str:
    """Normalize text for hallucination phrase comparisons."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def _is_hallucinated_segment(
    text: str,
    no_speech_prob: float = 0.0,
    avg_logprob: float = 0.0,
    compression_ratio: float = 1.0,
    duration: float = 1.0,
) -> bool:
    """
    Detect Whisper hallucination segments (e.g. 'blah blah blah', phantom outro
    phrases on silence/music, or low-confidence repetitive loops).
    """
    stripped = text.strip()
    if not stripped:
        return True

    norm = _normalize_text(stripped)
    norm_no_punct = re.sub(r"[^\w\s]", "", norm).strip()

    # 1. Pure punctuation / music symbol / empty after stripping symbols
    if not norm_no_punct:
        return True

    # 2. Pure babble hallucination ("blah blah blah", "la la la", "mm mm mm")
    if _BABBLE_ONLY_RE.match(stripped):
        logger.info(f"Filtered babble hallucination segment: {stripped!r}")
        return True

    # 3. High probability of silence / non-speech or severe decoding failure
    if no_speech_prob >= 0.72:
        logger.info(f"Filtered high no_speech_prob ({no_speech_prob:.2f}) segment: {stripped!r}")
        return True

    if no_speech_prob >= 0.48 and avg_logprob < -0.75:
        logger.info(
            f"Filtered low-confidence quiet segment (no_speech={no_speech_prob:.2f}, logprob={avg_logprob:.2f}): {stripped!r}"
        )
        return True

    if avg_logprob < -1.15:
        logger.info(f"Filtered very low avg_logprob ({avg_logprob:.2f}) segment: {stripped!r}")
        return True

    if compression_ratio > 2.4:
        logger.info(f"Filtered high compression_ratio ({compression_ratio:.2f}) loop: {stripped!r}")
        return True

    # 4. Known standalone Whisper silence hallucination boilerplate
    if norm in KNOWN_HALLUCINATION_PHRASES or norm_no_punct in KNOWN_HALLUCINATION_PHRASES:
        if no_speech_prob >= 0.25 or len(norm_no_punct.split()) <= 4:
            logger.info(f"Filtered known Whisper hallucination phrase: {stripped!r}")
            return True

    # 5. Severe inline repetition loop ("blah blah blah blah", "thank you thank you thank you thank you")
    if _REPETITION_LOOP_RE.search(stripped):
        # Check if repeated words dominate the segment (>60% of tokens are duplicates)
        words = re.findall(r"\b\w+\b", norm)
        if len(words) >= 6 and (len(set(words)) / len(words)) <= 0.35:
            logger.info(f"Filtered repetitive hallucination loop: {stripped!r}")
            return True

    # 6. Impossible speaking rate (>12 words/sec usually means hallucinated text stuffed into a 0.1s gap)
    word_count = len(norm_no_punct.split())
    if duration > 0 and word_count >= 5 and (word_count / max(duration, 0.1)) > 12.0:
        logger.info(f"Filtered impossible speech-rate hallucination ({word_count}w in {duration:.2f}s): {stripped!r}")
        return True

    return False


def _clean_segment_text(text: str) -> str:
    """Clean minor inline hallucination loops (e.g. stray trailing 'blah blah blah') while preserving genuine speech."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Collapse accidental 3+ consecutive repeats of "blah"
    cleaned = re.sub(r"(?:\bblah[\s,]*){3,}", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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
        key = f"v4_accurate_v3_{engine_tag}_{os.path.basename(video_path)}_{stat.st_size}_{int(stat.st_mtime)}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        return os.path.join(settings.TEMP_DIR, f"transcript_{digest}.json")
    except Exception:
        return ""


def _get_audio_chunk_duration(audio_path: str) -> float:
    """Get exact duration in seconds of an audio chunk via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        val = res.stdout.strip()
        if res.returncode == 0 and val and val != "N/A":
            return float(val)
    except Exception:
        pass
    return 600.0


def _extract_audio_chunks_for_cloud(video_path: str) -> list[str]:
    """
    Extract audio into 10-minute (600s) chunks (<12MB each) for Groq Cloud Whisper:
      1. First uses instant stream-copy segmentation (-c:a copy -f segment -segment_time 600),
         which finishes in 1-2s with 0% CPU even on a 1-hour or 2-hour video!
      2. Falls back to segmented 16kHz 24k mono AAC chunks only if stream copy fails or a chunk exceeds 23MB.
    """
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    copy_pattern = os.path.join(settings.TEMP_DIR, f"chunk_copy_{uid}_%03d.m4a")
    copy_glob = os.path.join(settings.TEMP_DIR, f"chunk_copy_{uid}_*.m4a")

    cmd_copy = [
        "ffmpeg", "-y", "-nostats", "-vn", "-sn", "-dn",
        "-i", video_path,
        "-c:a", "copy",
        "-f", "segment",
        "-segment_time", "600",
        "-reset_timestamps", "1",
        copy_pattern,
    ]
    try:
        res_copy = subprocess.run(cmd_copy, capture_output=True, text=True, timeout=180)
        chunks = sorted(glob.glob(copy_glob))
        if (
            res_copy.returncode == 0
            and chunks
            and all(1000 < os.path.getsize(c) < 23 * 1024 * 1024 for c in chunks)
        ):
            logger.info(
                f"Instant stream-copy audio extraction produced {len(chunks)} chunk(s) "
                f"({sum(os.path.getsize(c) for c in chunks)} bytes total)"
            )
            return chunks
    except Exception as e:
        logger.warning(f"Segmented audio stream copy skipped ({e}), falling back to 24k AAC chunks...")

    for c in glob.glob(copy_glob):
        try:
            os.remove(c)
        except Exception:
            pass

    enc_pattern = os.path.join(settings.TEMP_DIR, f"chunk_24k_{uid}_%03d.m4a")
    enc_glob = os.path.join(settings.TEMP_DIR, f"chunk_24k_{uid}_*.m4a")
    cmd_enc = [
        "ffmpeg", "-y", "-nostats", "-vn", "-sn", "-dn",
        "-i", video_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "aac",
        "-b:a", "24k",
        "-f", "segment",
        "-segment_time", "600",
        "-reset_timestamps", "1",
        enc_pattern,
    ]
    try:
        res_enc = subprocess.run(cmd_enc, capture_output=True, text=True, timeout=600)
        chunks = sorted(glob.glob(enc_glob))
        if res_enc.returncode == 0 and chunks:
            logger.info(f"Segmented 24k AAC audio extraction produced {len(chunks)} chunk(s)")
            return chunks
    except Exception as e:
        logger.warning(f"Segmented 24k AAC extraction failed: {e}")

    for c in glob.glob(enc_glob):
        try:
            os.remove(c)
        except Exception:
            pass

    raise RuntimeError("Failed to extract audio track from the uploaded video.")


def _extract_audio_for_transcription(video_path: str, for_cloud: bool = False) -> str:
    """Extract a single audio file for local faster-whisper fallback."""
    if for_cloud:
        chunks = _extract_audio_chunks_for_cloud(video_path)
        return chunks[0] if chunks else video_path

    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    speech_filter = "highpass=f=80,dynaudnorm=f=150:g=15:m=10"
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
        "-af", speech_filter,
        "-c:a", "pcm_s16le",
        temp_audio,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode == 0 and os.path.exists(temp_audio):
        return temp_audio
    logger.warning("Fast audio extraction failed, falling back to direct video path.")
    return video_path


def _call_groq_whisper_api(audio_path: str, groq_api_key: str, model_name: str) -> dict:
    """Execute a single multipart request to Groq's Whisper API."""
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

    add_field("model", model_name)
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
            "User-Agent": "ViralClipper/2.3",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Groq Cloud Whisper API ({model_name}) error ({e.code}): {err_body}")


def _transcribe_via_groq_cloud(
    audio_path: str,
    groq_api_key: str,
    time_offset: float = 0.0,
    prefer_turbo: bool = False,
) -> dict:
    """
    Transcribe a single audio file/chunk using Groq Cloud Whisper, applying time_offset
    to all segment and word timestamps.
    """
    data = None
    models_order = (
        ("whisper-large-v3-turbo", "whisper-large-v3")
        if prefer_turbo
        else ("whisper-large-v3", "whisper-large-v3-turbo")
    )
    used_model = models_order[0]
    last_err = None

    for candidate_model in models_order:
        try:
            logger.info(f"Transcribing via Groq Cloud LPU ('{candidate_model}', offset={time_offset:.1f}s)...")
            data = _call_groq_whisper_api(audio_path, groq_api_key, candidate_model)
            used_model = candidate_model
            break
        except Exception as e:
            last_err = e
            logger.warning(f"Groq model '{candidate_model}' failed: {e}")

    if data is None:
        raise RuntimeError(str(last_err or "Groq Cloud Whisper API failed"))

    raw_segments = data.get("segments", [])
    all_words = data.get("words", [])
    segments = []
    kept_words = []
    full_text_parts = []
    prev_end = time_offset

    for seg in raw_segments:
        raw_text = seg.get("text", "").strip()
        if not raw_text:
            continue

        raw_s_start = float(seg.get("start", 0.0))
        raw_s_end = float(seg.get("end", raw_s_start + 1.0))
        s_start = raw_s_start + time_offset
        s_end = raw_s_end + time_offset
        seg_dur = max(0.0, s_end - s_start)

        no_speech_prob = float(seg.get("no_speech_prob", 0.0) or 0.0)
        avg_logprob = float(seg.get("avg_logprob", 0.0) or 0.0)
        compression_ratio = float(seg.get("compression_ratio", 1.0) or 1.0)

        if _is_hallucinated_segment(
            raw_text,
            no_speech_prob=no_speech_prob,
            avg_logprob=avg_logprob,
            compression_ratio=compression_ratio,
            duration=seg_dur,
        ):
            continue

        text = _clean_segment_text(raw_text)
        if not text:
            continue

        seg_words = []
        for w in all_words:
            raw_w_start = float(w.get("start", 0.0))
            raw_w_end = float(w.get("end", raw_w_start))
            w_mid = (raw_w_start + raw_w_end) / 2.0
            if raw_s_start - 0.02 <= w_mid <= raw_s_end + 0.02:
                w_text = str(w.get("word", "")).strip()
                if w_text:
                    seg_words.append({
                        "start": round(raw_w_start + time_offset, 2),
                        "end": round(raw_w_end + time_offset, 2),
                        "word": w_text,
                    })

        if seg_words:
            s_start = max(prev_end, seg_words[0]["start"])
            s_end = max(s_start + 0.05, seg_words[-1]["end"])
            kept_words.extend(seg_words)
        else:
            s_start = max(prev_end, s_start)
            s_end = max(s_start + 0.05, s_end)

        prev_end = s_end

        segments.append({
            "start": round(s_start, 2),
            "end": round(s_end, 2),
            "text": text,
        })
        full_text_parts.append(text)

    result = {
        "full_text": " ".join(full_text_parts),
        "segments": segments,
        "words": kept_words,
        "language": data.get("language", "en"),
        "engine": f"{used_model} (Groq Cloud)",
    }
    logger.info(
        f"Groq Cloud {used_model} chunk complete: {len(segments)} clean segments (filtered {len(raw_segments) - len(segments)} hallucinated/silent)!"
    )
    return result


def transcribe_video(
    video_path: str,
    groq_api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """
    Transcribe a video file using Groq Cloud (with automatic 10-min stream-copy chunking
    for long videos so even 1-2 hour videos never stall at 25% or exceed 25MB),
    or fall back to local faster-whisper.
    """
    effective_groq_key = (groq_api_key or settings.GROQ_API_KEY or "").strip()
    engine_tag = "groq_v3_full" if effective_groq_key else f"local_{settings.WHISPER_MODEL}"

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

    # 1. Try Groq Cloud Whisper with stream-copy 10-minute chunking
    groq_error = None
    if effective_groq_key:
        chunks = []
        try:
            chunks = _extract_audio_chunks_for_cloud(video_path)
            total_chunks = len(chunks)
            all_segments = []
            all_words = []
            all_text_parts = []
            language = "en"
            engine_used = "whisper-large-v3 (Groq Cloud)"
            cumulative_offset = 0.0

            for idx, chunk_path in enumerate(chunks):
                if progress_callback:
                    try:
                        progress_callback(idx + 1, total_chunks)
                    except Exception:
                        pass

                chunk_dur = _get_audio_chunk_duration(chunk_path)
                chunk_res = _transcribe_via_groq_cloud(
                    chunk_path,
                    effective_groq_key,
                    time_offset=cumulative_offset,
                    prefer_turbo=(total_chunks > 1),
                )
                all_segments.extend(chunk_res.get("segments", []))
                all_words.extend(chunk_res.get("words", []))
                if chunk_res.get("full_text"):
                    all_text_parts.append(chunk_res["full_text"])
                language = chunk_res.get("language", language)
                engine_used = chunk_res.get("engine", engine_used)
                cumulative_offset += chunk_dur

                # Free disk/RAM immediately after each chunk finishes
                if os.path.exists(chunk_path):
                    try:
                        os.remove(chunk_path)
                    except Exception:
                        pass

            result = {
                "full_text": " ".join(all_text_parts),
                "segments": all_segments,
                "words": all_words,
                "language": language,
                "engine": engine_used,
            }
            if cache_path:
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(result, f)
                except Exception:
                    pass
            return result
        except Exception as e:
            groq_error = str(e)
            logger.warning(f"Groq Cloud transcription failed ({e}), falling back to local Whisper...")
        finally:
            for c in chunks:
                if c != video_path and os.path.exists(c):
                    try:
                        os.remove(c)
                    except Exception:
                        pass

    # 2. Local faster-whisper fallback (anti-hallucination settings enabled)
    logger.info(f"Starting local word-aligned transcription for: {video_path}")
    try:
        model = _get_model()
    except ImportError:
        if groq_error:
            raise RuntimeError(f"Groq Cloud transcription failed: {groq_error}")
        raise RuntimeError(
            "Cloud mode requires a free Groq API Key (console.groq.com/keys) in Settings -> Groq Whisper Key, "
            "because local faster-whisper is not installed on this lightweight cloud server."
        )

    audio_source = _extract_audio_for_transcription(video_path, for_cloud=False)
    is_temp = audio_source != video_path

    try:
        segments_iter, info = model.transcribe(
            audio_source,
            beam_size=5,
            best_of=5,
            temperature=(0.0, 0.2, 0.4, 0.6),
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            repetition_penalty=1.15,
            hallucination_silence_threshold=1.0,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=400,
                speech_pad_ms=250,
            ),
        )

        segments = []
        kept_words = []
        full_text_parts = []
        prev_end = 0.0

        for segment in segments_iter:
            raw_text = segment.text.strip()
            if not raw_text:
                continue

            no_speech_prob = float(getattr(segment, "no_speech_prob", 0.0) or 0.0)
            avg_logprob = float(getattr(segment, "avg_logprob", 0.0) or 0.0)
            compression_ratio = float(getattr(segment, "compression_ratio", 1.0) or 1.0)
            seg_dur = max(0.0, float(segment.end) - float(segment.start))

            if _is_hallucinated_segment(
                raw_text,
                no_speech_prob=no_speech_prob,
                avg_logprob=avg_logprob,
                compression_ratio=compression_ratio,
                duration=seg_dur,
            ):
                continue

            text = _clean_segment_text(raw_text)
            if not text:
                continue

            words = getattr(segment, "words", None)
            if words:
                seg_start = round(max(prev_end, words[0].start), 2)
                seg_end = round(max(seg_start + 0.05, words[-1].end), 2)
                for w in words:
                    w_text = str(getattr(w, "word", "")).strip()
                    if w_text:
                        kept_words.append({
                            "start": round(float(w.start), 2),
                            "end": round(float(w.end), 2),
                            "word": w_text,
                        })
            else:
                seg_start = round(max(prev_end, segment.start), 2)
                seg_end = round(max(seg_start + 0.05, segment.end), 2)

            prev_end = seg_end

            segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": text,
            })
            full_text_parts.append(text)

        result = {
            "full_text": " ".join(full_text_parts),
            "segments": segments,
            "words": kept_words,
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
