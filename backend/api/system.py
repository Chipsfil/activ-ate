from flask import Blueprint
from .common import *

bp = Blueprint("system", __name__)

@bp.get("/api/v1/health")
def health():
    try:
        with conn() as c: c.execute("SELECT 1")
        return {"status":"ok","database":"ok"}
    except psycopg.Error: return err("Database unavailable.", "server_error", 503)

