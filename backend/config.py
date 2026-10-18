"""Application configuration.

Edit these values on the server. Never commit real passwords or production
secrets to source control.
"""

# Local development example:
# DATABASE_URL = "postgresql://activate:PASSWORD@127.0.0.1:5432/activate"
DATABASE_URL = "postgresql://activate:CHANGE_THIS_PASSWORD@10.0.0.20:5432/activate?sslmode=require"
JWT_SECRET = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
# Set this to the public frontend URL on the backend VM.
FRONTEND_ORIGIN = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://FRONTEND_VM_PUBLIC_IP:8080",
]
# For a basic HTTP demo keep these values. Use HTTPS before handling real data.
COOKIE_SECURE = False
COOKIE_SAMESITE = "Lax"
HOST = "0.0.0.0"
PORT = 8000
