from flask import Blueprint
from .common import *

bp = Blueprint("community", __name__)

@bp.get("/api/v1/community/members/<mid>")
@auth_required
def member(mid): return err("Member not found.","not_found",404)
@bp.post("/api/v1/community/members/<mid>/cheers")
@auth_required
def cheer(mid): return err("This member cannot be cheered yet.","goal_not_reached",409)

for path, name, value in [
    ("/community/network","network",{"id":None,"member_count":1,"criteria":[],"explanation":"Your network is assigned automatically.","shared_data":["Exercise minutes","Workout type and duration","Streaks","Sleep hours","Water intake"]}),
    ("/community/leaderboard","leaderboard",{"habit":"exercise","unit":"min","period":"week","target_label":"Weekly target","rows":[],"summary":{"my_rank":1,"member_count":1}}),
    ("/community/insights","insights",{"habit":"exercise","items":[]}),
    ("/feed","feed",{"items":[]}),
]:
    bp.add_url_rule("/api/v1"+path,name,placeholder(name,value),methods=["GET"])
