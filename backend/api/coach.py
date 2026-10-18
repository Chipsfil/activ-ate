from flask import Blueprint
from .common import *

bp = Blueprint("coach", __name__)

bp.add_url_rule("/api/v1/coach/context", "coach_context", placeholder("coach_context", {"items": []}), methods=["GET"])

@bp.get("/api/v1/coach/conversations/latest")
@auth_required
def latest_chat(): return {"conversation_id":None,"messages":[]}
@bp.post("/api/v1/coach/conversations")
@auth_required
def new_chat(): return {"conversation_id":str(uuid.uuid4()),"messages":[]},201
@bp.post("/api/v1/coach/messages")
@auth_required
def chat_message(): return {"conversation_id":body().get("conversation_id"),"message":{"role":"assistant","content":"Keep following your goals and listen to your body.","created_at":datetime.now(timezone.utc).isoformat()},"proposed_sessions":[]}
