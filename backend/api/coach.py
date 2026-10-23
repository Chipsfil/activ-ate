from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, g

from .common import auth_required, body, conn, user_json

bp = Blueprint("coach", __name__)

PROMPTS = {
    "Build my training plan for next week":
        "Start with three sessions next week: one easy cardio session, one strength session, and one session for your favorite sport.",
    "What should I eat before my run?":
        "Have a light meal with carbohydrates and some protein one to two hours before running, and drink water.",
    "How can I get more protein?":
        "Add a protein source to each main meal, such as eggs, yogurt, beans, fish, chicken, or tofu.",
    "How do I compare to my network?":
        "Open Community to compare your exercise minutes with the other members this week.",
    "I feel tired – how can I sleep and recover better?":
        "Keep a regular sleep schedule, drink enough water, and add easy recovery days between harder workouts.",
}


@bp.get("/api/v1/coach/context")
@auth_required
def coach_context():
    with conn() as c:
        user = user_json(c, g.user_id)
        target = c.execute(
            "SELECT COALESCE(SUM(minutes_per_session*sessions_per_week),0) target "
            "FROM activity_goals WHERE user_id=%s", (g.user_id,),
        ).fetchone()["target"]
    return {"items": [
        {"label": "Name", "value": f"{user['first_name']} {user['last_name']}"},
        {"label": "Sports", "value": ", ".join(x["name"] for x in user["sports"]) or "No sports selected"},
        {"label": "Weekly activity target", "value": f"{int(target or 150)} minutes"},
    ]}


@bp.get("/api/v1/coach/conversations/latest")
@auth_required
def latest_chat():
    return {"conversation_id": None, "messages": []}


@bp.post("/api/v1/coach/conversations")
@auth_required
def new_chat():
    return {"conversation_id": str(uuid4()), "messages": []}, 201


@bp.post("/api/v1/coach/messages")
@auth_required
def chat_message():
    text = body().get("text", "").strip()
    answer = PROMPTS.get(text, "Choose one of the suggested questions to get a quick training tip.")
    return {
        "conversation_id": body().get("conversation_id") or str(uuid4()),
        "message": {
            "role": "assistant",
            "content": answer,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "proposed_sessions": [],
    }
