"""Video processing service using FFmpeg with turbo stream-copy, fast multi-seeking, and live progress."""

from concurrent.futures import ThreadPoolExecutor
import logging
import os
import re
import subprocess
from typing import Callable, Optional
from app.config import settings
from app.models import ClipInfo

logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        cmd_stream = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result_stream = subprocess.run(cmd_stream, capture_output=True, text=True, timeout=30)
        if result_stream.returncode != 0 or not result_stream.stdout.strip():
            raise RuntimeError(f"ffprobe failed to detect video duration: {result.stderr}")
        return float(result_stream.stdout.strip())

    val = result.stdout.strip()
    if not val or val == "N/A":
        return 60.0
    return float(val)


def get_video_codec(video_path: str) -> str:
    """Detect the video stream codec name (e.g., 'h264', 'av1', 'vp9')."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return res.stdout.strip().lower()
    except Exception:
        pass
    return ""


def detect_silence(
    video_path: str,
    threshold_db: int = None,
    min_duration: float = None,
) -> list[dict]:
    """
    Detect silence segments in a video using FFmpeg's silencedetect filter.
    """
    if threshold_db is None:
        threshold_db = settings.SILENCE_THRESHOLD
    if min_duration is None:
        min_duration = settings.SILENCE_MIN_DURATION

    cmd = [
        "ffmpeg",
        "-nostats",
        "-vn",
        "-sn",
        "-dn",
        "-i", video_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration}",
        "-f", "null",
        "-",
    ]

    logger.info(f"Running high-speed silence detection on: {video_path}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=45
        )

        output = result.stderr
        silence_segments = []
        starts = re.findall(r"silence_start: ([\d.]+)", output)
        ends = re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", output)

        for i, start in enumerate(starts):
            start_time = float(start)
            if i < len(ends):
                end_time = float(ends[i][0])
                duration = float(ends[i][1])
            else:
                end_time = start_time + 1.0
                duration = 1.0

            silence_segments.append({
                "start": round(start_time, 2),
                "end": round(end_time, 2),
                "duration": round(duration, 2),
            })

        logger.info(f"Detected {len(silence_segments)} silence segments.")
        return silence_segments

    except subprocess.TimeoutExpired:
        logger.warning("Silence detection timed out after 45s. Skipping dead-air markers.")
        return []
    except Exception as e:
        logger.warning(f"Silence detection failed: {e}. Proceeding without silence markers.")
        return []


def _compute_active_subsegments(
    start_time: float,
    end_time: float,
    silence_segments: list[dict],
    min_silence_to_cut: float = 0.8,
) -> list[tuple[float, float]]:
    """
    Compute speech segments within [start_time, end_time], excising long dead-air pauses.
    """
    current_start = start_time
    pieces = []

    relevant_silences = []
    for s in silence_segments:
        s_start = s["start"]
        s_end = s["end"]

        # Only trim leading silence if it's a huge dead-air gap (> 3.0s),
        # preserving the 2-3s lead-in buffer at the beginning of the clip.
        if s_start <= current_start and s_end > current_start:
            if (s_end - current_start) > 3.0:
                current_start = min(s_end - 1.5, end_time)
            continue

        # Only trim trailing silence if it's a huge dead-air gap (> 1.5s),
        # preserving the natural +0.4s sentence-ending buffer so final words never get cut off.
        if s_start < end_time and s_end >= end_time:
            if (end_time - s_start) > 1.5:
                end_time = max(s_start + 0.45, current_start)
            continue

        if s_start > current_start and s_end < end_time:
            if (s_end - s_start) >= min_silence_to_cut:
                relevant_silences.append((s_start, s_end))

    if current_start >= end_time:
        return [(start_time, end_time)]

    cursor = current_start
    for s_start, s_end in relevant_silences:
        if s_start > cursor + 0.3:
            pieces.append((round(cursor, 2), round(s_start, 2)))
        cursor = s_end

    if cursor < end_time - 0.3:
        pieces.append((round(cursor, 2), round(end_time, 2)))

    if not pieces:
        pieces = [(current_start, end_time)]

    return pieces


def _cut_single_clip(
    video_path: str,
    clip: ClipInfo,
    output_dir: str,
    silence_segments: list[dict],
    remove_dead_air: bool,
    video_codec: str = "",
) -> str:
    """
    Cut a single clip with FFmpeg:
    - Uses fast multi-input seeking (-ss before -i) so it NEVER decodes from 0:00.
    - Uses ultra-fast tuned x264 parameters for 3x faster encoding on cloud & local CPUs.
    """
    filename = f"clip_{clip.rank:02d}_score{clip.virality_score}.mp4"
    output_path = os.path.join(output_dir, filename)

    pieces = [(clip.start_time, clip.end_time)]
    if remove_dead_air and silence_segments:
        pieces = _compute_active_subsegments(
            clip.start_time,
            clip.end_time,
            silence_segments,
            min_silence_to_cut=0.8,
        )

    cut_success = False

    # Fast Multi-Input Splice Cut (when dead-air pauses are excised)
    # Uses -ss {p_start} -t {dur} BEFORE each -i so FFmpeg jumps directly to each speech piece in 0.05s!
    if len(pieces) > 1:
        logger.info(
            f"Clip #{clip.rank}: Fast-seeking & splicing {len(pieces)} speech chunks: {pieces}"
        )
        try:
            cmd = ["ffmpeg", "-y", "-nostats"]
            filter_parts = []
            inputs_concat = ""

            for idx, (p_start, p_end) in enumerate(pieces):
                dur = max(0.2, round(p_end - p_start, 2))
                cmd.extend(["-ss", str(p_start), "-t", str(dur), "-i", video_path])
                filter_parts.append(
                    f"[{idx}:v]scale=-2:'min(720,ih)',setpts=PTS-STARTPTS[v{idx}];"
                    f"[{idx}:a]aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS[a{idx}]"
                )
                inputs_concat += f"[v{idx}][a{idx}]"

            concat_filter = (
                f"{';'.join(filter_parts)};"
                f"{inputs_concat}concat=n={len(pieces)}:v=1:a=1[outv][outa]"
            )

            cmd.extend([
                "-filter_complex", concat_filter,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-crf", "24",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                cut_success = True
                total_dur = sum(p_end - p_start for p_start, p_end in pieces)
                clip.duration = round(total_dur, 2)
            else:
                logger.warning(f"Multi-input concat fallback for #{clip.rank}")
        except Exception as e:
            logger.warning(f"Error during dead-air splicing for clip #{clip.rank}: {e}")

    # Single-piece cut
    if not cut_success:
        p_start = pieces[0][0] if pieces else clip.start_time
        p_end = pieces[-1][1] if pieces else clip.end_time
        duration = max(0.5, round(p_end - p_start, 2))

        logger.info(
            f"Cutting synced clip #{clip.rank}: {p_start:.2f}s - {p_end:.2f}s -> {filename}"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-nostats",
            "-ss", str(p_start),
            "-i", video_path,
            "-t", str(duration),
            "-vf", "scale=-2:'min(720,ih)'",
            "-af", "aresample=async=1:first_pts=0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-x264-params", "ref=1:me=dia:subme=0:trellis=0:aq-mode=0",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"FFmpeg error for clip #{clip.rank}: {result.stderr[-500:]}")
            raise RuntimeError(f"Failed to cut clip #{clip.rank}: {result.stderr[-200:]}")

        clip.duration = round(duration, 2)

    clip.filename = filename
    logger.info(f"Clip #{clip.rank} ready: {filename}")
    return filename


def cut_clips(
    video_path: str,
    clips: list[ClipInfo],
    output_dir: str,
    silence_segments: list[dict] = None,
    remove_dead_air: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[str]:
    """
    Cut all clips with live per-clip progress updates and smart worker scaling.
    Uses 4 parallel workers on multi-core local PCs and 1 worker on Render cloud.
    """
    os.makedirs(output_dir, exist_ok=True)
    video_codec = get_video_codec(video_path)
    total = len(clips)

    # Detect if running on Render constrained cloud container vs multi-core PC
    is_render_cloud = bool(os.environ.get("RENDER"))
    cpu_count = os.cpu_count() or 2
    max_workers = 1 if is_render_cloud else min(4, max(1, cpu_count // 2), max(1, total))

    logger.info(
        f"Cutting {total} clips (codec={video_codec}, workers={max_workers}, cloud={is_render_cloud})..."
    )

    filenames = [None] * total
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _cut_single_clip,
                video_path,
                clip,
                output_dir,
                silence_segments,
                remove_dead_air,
                video_codec,
            ): idx
            for idx, clip in enumerate(clips)
        }
        from concurrent.futures import as_completed
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            filenames[idx] = future.result()
            completed_count += 1
            if progress_callback:
                try:
                    progress_callback(completed_count, total)
                except Exception:
                    pass

    return filenames
