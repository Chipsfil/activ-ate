from flask import Blueprint
from .common import *

bp = Blueprint("activity", __name__)

@bp.get("/api/v1/sports")
def sports():
    q=request.args.get("q","%").lower(); limit=min(int(request.args.get("limit",8)),50)
    with conn() as c:return {"items":[dict(id=r["id"],name=r["name"],category=r["category"],met=float(r["met"])) for r in c.execute("SELECT id,name,category,met FROM sports WHERE lower(name) LIKE %s OR %s=ANY(aliases) ORDER BY popularity DESC,name LIMIT %s",(f"%{q}%",q,limit))]}

@bp.put("/api/v1/daily-logs")
@auth_required
def daily_log():
    b=body(); d=parse_date(b.get("date"))
    if not d:return err("Date is required.","validation_error",422,"date")
    with conn() as c:
        c.execute("""INSERT INTO daily_logs(user_id,log_date,sleep_hours,water_l) VALUES(%s,%s,%s,%s)
          ON CONFLICT(user_id,log_date) DO UPDATE SET sleep_hours=EXCLUDED.sleep_hours,water_l=EXCLUDED.water_l""",(g.user_id,d,b.get("sleep_hours"),b.get("water_l"))); c.commit()
    return {"date":iso(d),"sleep_hours":b.get("sleep_hours"),"water_l":b.get("water_l")}

@bp.get("/api/v1/dashboard")
@auth_required
def dashboard():
    d = parse_date(request.args.get("date"), date.today())
    with conn() as c:
        log = c.execute("SELECT sleep_hours,water_l FROM daily_logs WHERE user_id=%s AND log_date=%s", (g.user_id, d)).fetchone()
        workouts = c.execute("SELECT COALESCE(sum(duration_min),0) minutes, count(*) sessions FROM workouts WHERE user_id=%s AND performed_on=%s AND status='done'", (g.user_id, d)).fetchone()
        return {"date": iso(d), "checkin": {"sleep_hours": float(log["sleep_hours"]) if log and log["sleep_hours"] is not None else None,
                "water_l": float(log["water_l"]) if log and log["water_l"] is not None else None},
                "today": {"minutes": int(workouts["minutes"]), "sessions": int(workouts["sessions"])},
                "totals": totals(c, g.user_id, d)}

@bp.get("/api/v1/workouts")
@auth_required
def list_workouts():
    limit=min(int(request.args.get("limit",20)),100); params=[g.user_id]; where="user_id=%s"
    if request.args.get("sport"):where+=" AND lower(sport_name)=lower(%s)";params.append(request.args["sport"])
    with conn() as c:
        rows=c.execute(f"SELECT * FROM workouts WHERE {where} ORDER BY performed_on DESC,created_at DESC LIMIT %s",(*params,limit)).fetchall()
        return {"items":[workout_json(r) for r in rows],"next_cursor":None}
def workout_json(r): return {**{k:r[k] for k in ("id","sport_name","title","performed_on","duration_min","distance_km","intensity","notes","kcal","status")}, "id":str(r["id"]),"sport":r["sport_name"],"sport_id":r["sport_id"],"performed_on":iso(r["performed_on"])}
@bp.post("/api/v1/workouts")
@auth_required
def create_workout():
    b=body(); d=parse_date(b.get("performed_on"),date.today())
    if not b.get("sport") or not b.get("duration_min"):return err("Sport and duration are required.")
    with conn() as c:
        s=sport(c,b.get("sport_id"),b["sport"]); kcal=round(float(s["met"])*current_weight(c,g.user_id)*float(b["duration_min"])/60); r=c.execute("""INSERT INTO workouts(user_id,sport_id,sport_name,title,performed_on,duration_min,distance_km,intensity,notes,kcal,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",(g.user_id,s["id"],b["sport"],b.get("title"),d,b["duration_min"],b.get("distance_km"),b.get("intensity","medium"),b.get("notes"),kcal,b.get("status","done"))).fetchone(); c.commit(); return {"workout":workout_json(r),"week":{"minutes":0,"target_minutes":150}},201
@bp.patch("/api/v1/workouts/<wid>")
@auth_required
def update_workout(wid):
    if "status" not in body():return err("No changes supplied.")
    with conn() as c:
        r=c.execute("UPDATE workouts SET status=%s WHERE id=%s AND user_id=%s RETURNING *",(body()["status"],wid,g.user_id)).fetchone()
        if not r:return err("Workout not found.","not_found",404)
        c.commit();return {"workout":workout_json(r),"week":{"minutes":0,"target_minutes":150}}
@bp.delete("/api/v1/workouts/<wid>")
@auth_required
def delete_workout(wid):
    with conn() as c:c.execute("DELETE FROM workouts WHERE id=%s AND user_id=%s",(wid,g.user_id));c.commit()
    return "",204
@bp.get("/api/v1/workouts/stats")
@auth_required
def workout_stats(): return {"weeks":[]}

