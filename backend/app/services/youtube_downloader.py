"""
YouTube video download service with multi-layer Cloud Anti-Bot Bypass:
1. yt-dlp Mobile/Embedded Player Client Rotation (tv_embedded, ios, android_vr, mweb)
2. Automatic Piped / Invidious / Cobalt API Cloud Proxy Fallback when datacenter IPs are blocked.
"""

import json
import logging
import os
import re
import subprocess
import urllib.request
import urllib.error
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


def extract_video_id(url: str) -> str:
    """Extract the 11-character YouTube video ID."""
    match = YOUTUBE_REGEX.search(url.strip())
    return match.group(5) if match else ""


def _download_via_piped_or_invidious(video_id: str, output_path: str) -> dict:
    """
    Fallback downloader using public Piped & Invidious API instances
    when YouTube blocks a cloud server's datacenter IP address.
    """
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.tokhmi.xyz",
        "https://pipedapi.moomoo.me",
        "https://pipedapi.syncpundit.io",
        "https://api.piped.private.coffee",
    ]

    for instance in piped_instances:
        try:
            api_url = f"{instance}/streams/{video_id}"
            logger.info(f"Trying Piped cloud relay: {api_url}")
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            title = data.get("title", "YouTube Video")
            duration = float(data.get("duration", 0.0) or 0.0)
            uploader = data.get("uploader", "YouTube Creator")

            # Check muxed streams first, or pair video + audio stream
            video_streams = data.get("videoStreams", [])
            audio_streams = data.get("audioStreams", [])

            muxed = [
                s for s in video_streams
                if not s.get("videoOnly", True) and s.get("url")
            ]
            if muxed:
                stream_url = muxed[0]["url"]
                cmd = [
                    "ffmpeg", "-y", "-nostats",
                    "-i", stream_url,
                    "-c", "copy",
                    output_path,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                if res.returncode == 0 and os.path.exists(output_path):
                    return {
                        "video_path": output_path,
                        "title": title,
                        "duration": duration,
                        "uploader": uploader,
                        "file_size": os.path.getsize(output_path),
                    }

            # Otherwise combine best <=720p videoOnly stream + audio stream via FFmpeg
            vid_only = [
                s for s in video_streams
                if s.get("url") and s.get("height", 720) <= 720
            ]
            if vid_only and audio_streams:
                v_url = vid_only[0]["url"]
                a_url = audio_streams[0]["url"]
                cmd = [
                    "ffmpeg", "-y", "-nostats",
                    "-i", v_url,
                    "-i", a_url,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    output_path,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
                if res.returncode == 0 and os.path.exists(output_path):
                    return {
                        "video_path": output_path,
                        "title": title,
                        "duration": duration,
                        "uploader": uploader,
                        "file_size": os.path.getsize(output_path),
                    }
        except Exception as e:
            logger.warning(f"Piped instance {instance} failed: {e}")

    # Try Invidious API instances as secondary fallback
    invidious_instances = [
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de",
        "https://invidious.privacyredirect.com",
    ]
    for instance in invidious_instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            logger.info(f"Trying Invidious cloud relay: {api_url}")
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            title = data.get("title", "YouTube Video")
            duration = float(data.get("lengthSeconds", 0.0) or 0.0)
            uploader = data.get("author", "YouTube Creator")
            format_streams = data.get("formatStreams", [])
            if format_streams:
                stream_url = format_streams[0].get("url")
                if stream_url:
                    cmd = [
                        "ffmpeg", "-y", "-nostats",
                        "-i", stream_url,
                        "-c", "copy",
                        output_path,
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                    if res.returncode == 0 and os.path.exists(output_path):
                        return {
                            "video_path": output_path,
                            "title": title,
                            "duration": duration,
                            "uploader": uploader,
                            "file_size": os.path.getsize(output_path),
                        }
        except Exception as e:
            logger.warning(f"Invidious instance {instance} failed: {e}")

    raise RuntimeError(
        "YouTube blocked the cloud datacenter IP across all player clients and relays. "
        "Try uploading the MP4 file directly or using the local server for this specific video."
    )


def download_youtube_video(url: str, job_id: str) -> dict:
    """
    Download a YouTube video to the uploads directory.
    Rotates across non-web player clients (android_vr, tv_embedded, ios, mweb)
    to bypass YouTube's 'Sign in to confirm you're not a bot' check on cloud servers.
    """
    clean_url = url.strip()
    if not is_valid_youtube_url(clean_url):
        raise ValueError("Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.")

    video_id = extract_video_id(clean_url)
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(settings.UPLOAD_DIR, output_filename)
    output_template = os.path.join(settings.UPLOAD_DIR, f"{job_id}.%(ext)s")

    # Client profiles ordered by highest success rate on cloud datacenter IPs without cookies
    client_profiles = [
        ["android_vr", "tv", "ios"],
        ["ios", "mweb"],
        ["tv_embedded", "android_creator"],
        ["web_creator", "mediaconnect"],
    ]

    last_error = None

    for clients in client_profiles:
        ydl_opts = {
            "format": (
                "bestvideo[height<=720][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
                "best[height<=720][ext=mp4]/best[height<=720]/bestvideo+bestaudio/best"
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
                    "player_skip": ["webpage", "configs"],
                }
            },
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Mobile Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        try:
            logger.info(f"Trying YouTube download with player_client={clients} -> Job {job_id}")
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
                logger.info(f"YouTube download succeeded via {clients}: '{title}' ({file_size} bytes)")
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

    # If all yt-dlp player_client profiles hit the bot check on the cloud IP, fall back to Piped/Invidious relay
    if video_id:
        logger.info(f"All yt-dlp profiles blocked by YouTube datacenter check. Falling back to cloud relay for {video_id}...")
        try:
            return _download_via_piped_or_invidious(video_id, output_path)
        except Exception as relay_err:
            logger.warning(f"Cloud relay fallback also failed: {relay_err}")

    raise RuntimeError(f"Failed to download YouTube video: {last_error}")
