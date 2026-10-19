from datetime import date, timedelta

from flask import Blueprint, g, request

from .common import (
    auth_required,
    body,
    conn,
    current_weight,
    err,
    iso,
    parse_date,
    sport,
    totals,
)

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
        week_start = d - timedelta(days=d.weekday())
        week = _week_summary(c, g.user_id, week_start)
        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            row = c.execute(
                "SELECT COALESCE(sum(duration_min),0) minutes FROM workouts "
                "WHERE user_id=%s AND performed_on=%s AND status='done'",
                (g.user_id, day),
            ).fetchone()
            days.append({"date": iso(day), "minutes": None if day > date.today() else int(row["minutes"])})
        day_totals = totals(c, g.user_id, d)
        return {
            "date": iso(d),
            "checkin": {
                "sleep_hours": float(log["sleep_hours"]) if log and log["sleep_hours"] is not None else None,
                "water_l": float(log["water_l"]) if log and log["water_l"] is not None else None,
            },
            "today": {
                "minutes": int(workouts["minutes"]),
                "sessions": int(workouts["sessions"]),
                "kcal": day_totals["kcal"],
                "kcal_target": 2350,
                "protein_g": day_totals["protein_g"],
                "protein_target_g": 140,
                "sleep_hours": float(log["sleep_hours"]) if log and log["sleep_hours"] is not None else None,
                "water_l": float(log["water_l"]) if log and log["water_l"] is not None else None,
            },
            "week": week,
            "days": days,
            "streak": {"current": 0, "best": 0},
            "goal_progress": [],
            "recent_workouts": [],
            "network_top": [],
            "network_note": "",
            "feed": [],
        }

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
def workout_stats():
    count = min(int(request.args.get("weeks", 8)), 26)
    current_week = date.today() - timedelta(days=date.today().weekday())
    with conn() as c:
        weeks = []
        for offset in range(count - 1, -1, -1):
            start = current_week - timedelta(days=offset * 7)
            row = c.execute(
                "SELECT COALESCE(sum(duration_min),0) minutes FROM workouts "
                "WHERE user_id=%s AND performed_on BETWEEN %s AND %s AND status='done'",
                (g.user_id, start, start + timedelta(days=6)),
            ).fetchone()
            weeks.append({"week_start": iso(start), "minutes": int(row["minutes"])})

        by_sport = c.execute(
            "SELECT sport_name sport, COALESCE(sum(duration_min),0) minutes "
            "FROM workouts WHERE user_id=%s AND performed_on BETWEEN %s AND %s "
            "AND status='done' GROUP BY sport_name ORDER BY minutes DESC",
            (g.user_id, current_week, current_week + timedelta(days=6)),
        ).fetchall()
        target = c.execute(
            "SELECT COALESCE(sum(minutes_per_session * sessions_per_week),0) target "
            "FROM activity_goals WHERE user_id=%s",
            (g.user_id,),
        ).fetchone()["target"] or 150
        week = _week_summary(c, g.user_id, current_week, target)
        longest = c.execute(
            "SELECT sport_name sport, duration_min, performed_on FROM workouts "
            "WHERE user_id=%s AND status='done' ORDER BY duration_min DESC LIMIT 1",
            (g.user_id,),
        ).fetchone()
        personal_bests = []
        if longest:
            personal_bests.append({
                "label": "Longest session",
                "value": f"{longest['duration_min']} min",
                "detail": f"{longest['sport']}, {iso(longest['performed_on'])}",
            })
        personal_bests.append({
            "label": "Best week",
            "value": f"{max((item['minutes'] for item in weeks), default=0)} min",
            "detail": f"last {count} weeks",
        })
        return {
            "weeks": weeks,
            "target_minutes": int(target),
            "week": week,
            "by_sport": [dict(row) for row in by_sport],
            "goal_progress": [],
            "personal_bests": personal_bests,
        }


def _week_summary(c, uid, start, target=None):
    row = c.execute(
        "SELECT COALESCE(sum(duration_min),0) minutes, count(*) sessions_done "
        "FROM workouts WHERE user_id=%s AND performed_on BETWEEN %s AND %s AND status='done'",
        (uid, start, start + timedelta(days=6)),
    ).fetchone()
    if target is None:
        target_row = c.execute(
            "SELECT COALESCE(sum(minutes_per_session * sessions_per_week),0) target "
            "FROM activity_goals WHERE user_id=%s",
            (uid,),
        ).fetchone()
        target = target_row["target"] or 150
    planned = c.execute(
        "SELECT COALESCE(sum(sessions_per_week),0) sessions "
        "FROM activity_goals WHERE user_id=%s",
        (uid,),
    ).fetchone()["sessions"] or 0
    return {
        "minutes": int(row["minutes"]),
        "target_minutes": int(target),
        "sessions_done": int(row["sessions_done"]),
        "sessions_planned": int(planned),
    }
