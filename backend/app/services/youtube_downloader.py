"""
YouTube video download service using:
1. pytubefix (with built-in Node.js Proof-of-Origin / PoToken generator for ANDROID, MWEB, WEB, IOS)
2. yt-dlp fallback
"""

import logging
import os
import re
import yt_dlp
from app.config import settings

logger = logging.getLogger(__name__)

# Matches standard watch URLs, shorts, embed, and youtu.be links
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?.*?v=|shorts/|embed/)|youtu\.be/)([\w\-]{11})",
    re.IGNORECASE,
)


def is_valid_youtube_url(url: str) -> bool:
    """Check if the provided URL is a valid YouTube link."""
    if not url or not isinstance(url, str):
        return False
    return bool(YOUTUBE_REGEX.search(url.strip()))


def _download_via_pytubefix(clean_url: str, output_dir: str, output_filename: str) -> dict:
    """
    Download YouTube video using pytubefix with automatic PoToken generation
    (bypasses cloud datacenter bot checks without requiring cookies or accounts).
    """
    from pytubefix import YouTube

    clients = ["ANDROID", "MWEB", "WEB", "IOS", "ANDROID_VR"]
    last_err = None

    for client in clients:
        try:
            logger.info(f"Trying pytubefix download with client={client} (auto PoToken)...")
            yt = YouTube(clean_url, client=client)
            title = yt.title or "YouTube Video"
            duration = float(yt.length or 0.0)
            uploader = yt.author or "YouTube Creator"

            # Prefer progressive MP4 stream (contains both video + audio, zero merge overhead)
            stream = (
                yt.streams.filter(progressive=True, file_extension="mp4")
                .order_by("resolution")
                .desc()
                .first()
            )
            if not stream:
                stream = yt.streams.filter(progressive=True).first()

            if stream:
                final_path = os.path.join(output_dir, output_filename)
                if os.path.exists(final_path):
                    os.remove(final_path)
                stream.download(output_path=output_dir, filename=output_filename)
                if os.path.exists(final_path) and os.path.getsize(final_path) > 1000:
                    file_size = os.path.getsize(final_path)
                    logger.info(
                        f"pytubefix ({client}) succeeded: '{title}' ({file_size} bytes)"
                    )
                    return {
                        "video_path": final_path,
                        "title": title,
                        "duration": duration,
                        "uploader": uploader,
                        "file_size": file_size,
                    }
        except Exception as e:
            last_err = e
            logger.warning(f"pytubefix ({client}) failed: {e}")

    raise RuntimeError(f"pytubefix clients exhausted: {last_err}")


def download_youtube_video(url: str, job_id: str) -> dict:
    """
    Download a YouTube video to the uploads directory.
    Uses pytubefix (with built-in Node.js PoToken generator) first, then yt-dlp fallback.
    """
    clean_url = url.strip()
    if not is_valid_youtube_url(clean_url):
        raise ValueError("Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(settings.UPLOAD_DIR, output_filename)
    output_template = os.path.join(settings.UPLOAD_DIR, f"{job_id}.%(ext)s")

    # 1. Primary Cloud Engine: pytubefix with built-in Node.js Proof-of-Origin (PoToken)
    try:
        return _download_via_pytubefix(clean_url, settings.UPLOAD_DIR, output_filename)
    except Exception as e:
        logger.warning(f"pytubefix primary download failed ({e}), trying yt-dlp fallback...")

    # 2. Secondary Engine: yt-dlp with mobile/VR player clients
    client_profiles = [
        ["android_vr", "ios"],
        ["mweb", "ios"],
        ["mediaconnect", "web_creator"],
    ]

    last_error = None
    for clients in client_profiles:
        ydl_opts = {
            "format": (
                "bestvideo[height<=720][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
                "best[height<=720][ext=mp4]/best[height<=720]/best"
            ),
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "concurrent_fragment_downloads": 4,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 45,
            "nocheckcertificate": True,
            "extractor_args": {
                "youtube": {
                    "player_client": clients,
                }
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                title = info.get("title", "YouTube Video")
                duration = float(info.get("duration", 0.0) or 0.0)
                uploader = info.get("uploader", "Unknown Creator")

            final_path = output_path
            if not os.path.exists(final_path):
                base = os.path.join(settings.UPLOAD_DIR, job_id)
                for ext in [".mp4", ".mkv", ".webm"]:
                    test_path = base + ext
                    if os.path.exists(test_path):
                        final_path = test_path
                        break

            if os.path.exists(final_path) and os.path.getsize(final_path) > 1000:
                file_size = os.path.getsize(final_path)
                return {
                    "video_path": final_path,
                    "title": title,
                    "duration": duration,
                    "uploader": uploader,
                    "file_size": file_size,
                }
        except Exception as e:
            last_error = e
            logger.warning(f"yt-dlp profile {clients} failed: {e}")

    raise RuntimeError(f"Failed to download YouTube video: {last_error}")
