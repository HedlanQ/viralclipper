"""
Hugging Face Spaces Free-Tier Entrypoint (Gradio SDK Mode).
Runs the full ViralClipper FastAPI + HTML5 Frontend on port 7860 without requiring Docker.
"""

import os
import sys
import uvicorn

# Add backend directory to Python path and switch working directory so paths resolve cleanly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from app.main import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
