from flask import Blueprint
from .common import *

bp = Blueprint("recommendations", __name__)

for path, name, value in [
    ("/recommendations/daily", "rec_daily", {
        "workout": "Keep moving toward your weekly target.",
        "nutrition": "Aim for balanced meals.",
        "suggested_session": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }),
    ("/recommendations/workout", "rec_workout", {
        "text": "Follow your planned sessions consistently.",
        "tips": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }),
    ("/recommendations/nutrition", "rec_nutrition", {
        "text": "Use your nutrition targets as a guide.",
        "more_of": [],
        "watch": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }),
]:
    bp.add_url_rule("/api/v1" + path, name, placeholder(name, value), methods=["GET"])
