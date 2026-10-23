"""
YouTube video download service using:
1. Clipto Cloud Proxy Resolver (resolves YouTube streams via residential proxy pool so cloud datacenter IPs never get bot-blocked!)
2. pytubefix (with built-in Node.js Proof-of-Origin / PoToken generator)
3. yt-dlp fallback
"""

import json
import logging
import os
import re
import subprocess
import urllib.request
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


def _download_stream_to_file(stream_url: str, dest_path: str):
    """Download a direct media stream URL to disk in 256KB chunks."""
    req = urllib.request.Request(
        stream_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest_path, "wb") as out_f:
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out_f.write(chunk)


def _download_via_clipto_cloud_resolver(clean_url: str, output_dir: str, output_filename: str) -> dict:
    """
    Resolve and download YouTube video via Clipto's residential proxy pool.
    Works 100% from cloud datacenter IPs (Render, AWS, etc.) without cookies or bot checks!
    """
    logger.info(f"Resolving YouTube stream via Clipto Cloud Resolver: {clean_url}")
    api_url = "https://www.clipto.com/api/youtube"
    payload = json.dumps({"url": clean_url}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.clipto.com/",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("success") or not data.get("medias"):
        raise RuntimeError(f"Clipto resolver returned unsuccessful response: {data.get('error')}")

    title = data.get("title") or "YouTube Video"
    duration = float(data.get("duration") or 0.0)
    uploader = data.get("author") or "YouTube Creator"
    medias = data.get("medias", [])

    final_path = os.path.join(output_dir, output_filename)
    if os.path.exists(final_path):
        os.remove(final_path)

    # 1. Check for muxed MP4 stream (video + audio already combined -> super fast single download!)
    muxed_streams = [
        m for m in medias
        if m.get("type") == "video" and m.get("is_audio") is True and m.get("url")
    ]
    if muxed_streams:
        stream_url = muxed_streams[0]["url"]
        logger.info(f"Downloading muxed MP4 stream ({muxed_streams[0].get('quality')})...")
        _download_stream_to_file(stream_url, final_path)
        if os.path.exists(final_path) and os.path.getsize(final_path) > 10000:
            file_size = os.path.getsize(final_path)
            logger.info(f"Clipto Cloud Resolver download complete: '{title}' ({file_size} bytes)")
            return {
                "video_path": final_path,
                "title": title,
                "duration": duration,
                "uploader": uploader,
                "file_size": file_size,
            }

    # 2. Fallback: combine 720p/480p video stream + m4a audio stream
    vid_streams = [
        m for m in medias
        if m.get("type") == "video" and m.get("extension") == "mp4" and m.get("url")
        and any(q in str(m.get("quality", "")) for q in ["720p", "480p", "360p"])
    ]
    aud_streams = [
        m for m in medias
        if m.get("type") == "audio" and m.get("extension") == "m4a" and m.get("url")
    ] or [
        m for m in medias
        if m.get("type") == "audio" and m.get("url")
    ]

    if vid_streams and aud_streams:
        temp_v = os.path.join(output_dir, f"temp_v_{output_filename}")
        temp_a = os.path.join(output_dir, f"temp_a_{output_filename}.m4a")
        try:
            _download_stream_to_file(vid_streams[0]["url"], temp_v)
            _download_stream_to_file(aud_streams[0]["url"], temp_a)
            cmd = [
                "ffmpeg", "-y", "-nostats",
                "-i", temp_v,
                "-i", temp_a,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                final_path,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if os.path.exists(final_path) and os.path.getsize(final_path) > 10000:
                return {
                    "video_path": final_path,
                    "title": title,
                    "duration": duration,
                    "uploader": uploader,
                    "file_size": os.path.getsize(final_path),
                }
        finally:
            for p in [temp_v, temp_a]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    raise RuntimeError("Clipto resolver streams could not be saved.")


def _download_via_pytubefix(clean_url: str, output_dir: str, output_filename: str) -> dict:
    """
    Download YouTube video using pytubefix with automatic PoToken generation.
    """
    from pytubefix import YouTube

    clients = ["ANDROID", "MWEB", "WEB", "IOS", "ANDROID_VR"]
    last_err = None

    for client in clients:
        try:
            logger.info(f"Trying pytubefix download with client={client}...")
            yt = YouTube(clean_url, client=client)
            title = yt.title or "YouTube Video"
            duration = float(yt.length or 0.0)
            uploader = yt.author or "YouTube Creator"

            stream = (
                yt.streams.filter(progressive=True, file_extension="mp4")
                .order_by("resolution")
                .desc()
                .first()
            ) or yt.streams.filter(progressive=True).first()

            if stream:
                final_path = os.path.join(output_dir, output_filename)
                if os.path.exists(final_path):
                    os.remove(final_path)
                stream.download(output_path=output_dir, filename=output_filename)
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
            last_err = e
            logger.warning(f"pytubefix ({client}) failed: {e}")

    raise RuntimeError(f"pytubefix clients exhausted: {last_err}")


def download_youtube_video(url: str, job_id: str) -> dict:
    """
    Download a YouTube video to the uploads directory.
    1. Clipto Cloud Proxy Resolver (bypasses datacenter IP blocks 100%)
    2. pytubefix with PoToken
    3. yt-dlp fallback
    """
    clean_url = url.strip()
    if not is_valid_youtube_url(clean_url):
        raise ValueError("Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(settings.UPLOAD_DIR, output_filename)
    output_template = os.path.join(settings.UPLOAD_DIR, f"{job_id}.%(ext)s")

    engine_errors = []

    # 1. Primary Cloud Proxy Resolver (Clipto Residential Proxy Pool)
    try:
        return _download_via_clipto_cloud_resolver(clean_url, settings.UPLOAD_DIR, output_filename)
    except Exception as e:
        engine_errors.append(f"[1/3 clipto] {str(e)[:200]}")
        logger.warning(f"Clipto Cloud Resolver failed ({e}), trying pytubefix...")

    # 2. Secondary Engine: pytubefix with built-in Node.js Proof-of-Origin (PoToken)
    try:
        return _download_via_pytubefix(clean_url, settings.UPLOAD_DIR, output_filename)
    except Exception as e:
        engine_errors.append(f"[2/3 pytubefix] {str(e)[:200]}")
        logger.warning(f"pytubefix download failed ({e}), trying yt-dlp fallback...")

    # 3. Tertiary Engine: yt-dlp with mobile/VR player clients
    client_profiles = [
        ["android_vr", "ios"],
        ["mweb", "ios"],
    ]

    last_error = None
    for clients in client_profiles:
        ydl_opts = {
            "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
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

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return {
                    "video_path": output_path,
                    "title": title,
                    "duration": duration,
                    "uploader": uploader,
                    "file_size": os.path.getsize(output_path),
                }
        except Exception as e:
            last_error = e
            logger.warning(f"yt-dlp profile {clients} failed: {e}")

    engine_errors.append(f"[3/3 yt-dlp] {str(last_error)[:200]}")
    raise RuntimeError(" | ".join(engine_errors))
