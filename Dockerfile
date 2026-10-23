FROM python:3.11-slim

# Install FFmpeg and system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install lightweight cloud dependencies (~80MB RAM usage, no heavy local PyTorch/Whisper weights)
COPY backend/requirements-cloud.txt ./backend/requirements-cloud.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements-cloud.txt && \
    pip install --no-cache-dir --upgrade --pre "yt-dlp[default]" bgutil-ytdlp-pot-provider

# Copy application code
COPY backend ./backend
COPY frontend ./frontend

# Ensure writable directories exist for uploads, outputs, and temp cache
RUN mkdir -p backend/uploads backend/output backend/temp && \
    chmod -R 777 backend/uploads backend/output backend/temp

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
