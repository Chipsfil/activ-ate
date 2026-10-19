"""Settings used by the backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

# Required settings
DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]

# Use the single frontend address that the browser uses to open the app.
FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN",
    "http://localhost:8080",
).strip()

# Optional settings
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
