import math
from datetime import date, timedelta

from flask import Blueprint, g, request

from .common import auth_required, body, conn, current_weight, err, iso, parse_date

bp = Blueprint("activity", __name__)


def workout_json(row):
    return {
        "id": str(row["id"]),
        "sport": row["sport_name"],
        "sport_id": row["sport_id"],
        "title": row["title"],
        "performed_on": iso(row["performed_on"]),
        "duration_min": row["duration_min"],
        "distance_km": float(row["distance_km"]) if row["distance_km"] is not None else None,
        "intensity": row["intensity"],
        "notes": row["notes"],
        "kcal": row["kcal"],
        "status": row["status"],
        "created_at": iso(row["created_at"]),
    }


def week_summary(c, start, target=None):
    row = c.execute(
        "SELECT COALESCE(sum(duration_min),0) minutes, count(*) sessions "
        "FROM workouts WHERE user_id=%s AND performed_on BETWEEN %s AND %s AND status='done'",
        (g.user_id, start, start + timedelta(days=6)),
    ).fetchone()
    planned = c.execute(
        "SELECT COALESCE(sum(sessions_per_week),0) sessions "
        "FROM activity_goals WHERE user_id=%s", (g.user_id,),
    ).fetchone()["sessions"]
    if target is None:
        target = c.execute(
            "SELECT COALESCE(sum(minutes_per_session*sessions_per_week),0) target "
            "FROM activity_goals WHERE user_id=%s", (g.user_id,),
        ).fetchone()["target"] or 150
    return {
        "minutes": int(row["minutes"]),
        "target_minutes": int(target),
        "sessions_done": int(row["sessions"]),
        "sessions_planned": int(planned),
    }


def goal_progress(c, start, end):
    goals = c.execute(
        "SELECT sport_id,sport_name,minutes_per_session,sessions_per_week "
        "FROM activity_goals WHERE user_id=%s ORDER BY sport_name",
        (g.user_id,),
    ).fetchall()
    result = []
    for goal in goals:
        done = c.execute(
            "SELECT count(*) sessions FROM workouts "
            "WHERE user_id=%s AND status='done' AND performed_on BETWEEN %s AND %s "
            "AND (sport_id=%s OR lower(sport_name)=lower(%s))",
            (g.user_id, start, end, goal["sport_id"], goal["sport_name"]),
        ).fetchone()["sessions"]
        result.append({
            "kind": "activity",
            "label": f"{goal['sport_name']} · {goal['minutes_per_session']} min · {goal['sessions_per_week']}×/week",
            "done": int(done),
            "target": int(goal["sessions_per_week"]),
            "unit": "sessions",
        })
    return result


def streak_summary(c, user_id, today=None):
    today = today or date.today()
    active_dates = {
        row["active_date"]
        for row in c.execute(
            "SELECT performed_on AS active_date FROM workouts "
            "WHERE user_id=%s AND status='done'",
            (user_id,),
        )
    }

    current_day = today if today in active_dates else today - timedelta(days=1)
    current = 0
    while current_day in active_dates:
        current += 1
        current_day -= timedelta(days=1)

    best = 0
    run = 0
    for offset in range(120, -1, -1):
        if today - timedelta(days=offset) in active_dates:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return {"current": current, "best": best}


def personal_bests(c, user_id, weeks):
    rows = c.execute(
        "SELECT sport_name,performed_on,duration_min,distance_km "
        "FROM workouts WHERE user_id=%s AND status='done'",
        (user_id,),
    ).fetchall()
    bests = []
    if rows:
        longest = max(rows, key=lambda row: row["duration_min"])
        bests.append({
            "label": "Longest session",
            "value": f"{longest['duration_min']} min",
            "detail": f"{longest['sport_name']}, {iso(longest['performed_on'])}",
        })

        with_distance = [row for row in rows if row["distance_km"] is not None]
        if with_distance:
            farthest = max(with_distance, key=lambda row: row["distance_km"])
            bests.append({
                "label": "Longest distance",
                "value": f"{float(farthest['distance_km']):g} km",
                "detail": farthest["sport_name"],
            })

        qualifying_runs = [
            row for row in with_distance
            if row["distance_km"] >= 5
            and any(term in row["sport_name"].lower() for term in ("run", "jog"))
        ]
        if qualifying_runs:
            estimated_five_k = min(
                (row["duration_min"] / float(row["distance_km"])) * 5
                for row in qualifying_runs
            )
            minutes = math.floor(estimated_five_k)
            seconds = math.floor((estimated_five_k - minutes) * 60 + 0.5)
            if seconds == 60:
                minutes += 1
                seconds = 0
            bests.append({
                "label": "5 km (estimated)",
                "value": f"{minutes}:{seconds:02d}",
                "detail": "from your average pace",
            })

    bests.append({
        "label": "Best week",
        "value": f"{max((week['minutes'] for week in weeks), default=0)} min",
        "detail": f"last {len(weeks)} weeks",
    })
    return bests


@bp.get("/api/v1/sports")
def sports():
    query = request.args.get("q", "").strip().lower()
    try:
        limit = min(max(int(request.args.get("limit", 8)), 1), 50)
    except ValueError:
        limit = 8
    pattern = f"%{query}%"
    with conn() as c:
        rows = c.execute(
            "SELECT id,name,category,met FROM sports "
            "WHERE %s='' OR lower(name) LIKE %s OR EXISTS "
            "(SELECT 1 FROM unnest(aliases) a WHERE lower(a) LIKE %s) "
            "ORDER BY popularity DESC,name LIMIT %s",
            (query, pattern, pattern, limit),
        )
        return {"items": [
            {"id": r["id"], "name": r["name"], "category": r["category"], "met": float(r["met"])}
            for r in rows
        ]}


@bp.put("/api/v1/daily-logs")
@auth_required
def save_daily_log():
    values = body()
    day = parse_date(values.get("date"))
    if not day:
        return err("Date is required.", "validation_error", 422, "date")
    with conn() as c:
        c.execute(
            "INSERT INTO daily_logs(user_id,log_date,sleep_hours,water_l) "
            "VALUES(%s,%s,%s,%s) ON CONFLICT(user_id,log_date) DO UPDATE SET "
            "sleep_hours=EXCLUDED.sleep_hours,water_l=EXCLUDED.water_l",
            (g.user_id, day, values.get("sleep_hours"), values.get("water_l")),
        )
        c.commit()
    return {"date": iso(day), "sleep_hours": values.get("sleep_hours"), "water_l": values.get("water_l")}


@bp.get("/api/v1/dashboard")
@auth_required
def dashboard():
    day = parse_date(request.args.get("date"), date.today())
    if not day:
        return err("Invalid date.", "validation_error", 422, "date")
    start = day - timedelta(days=day.weekday())
    with conn() as c:
        log = c.execute(
            "SELECT sleep_hours,water_l FROM daily_logs WHERE user_id=%s AND log_date=%s",
            (g.user_id, day),
        ).fetchone()
        today_sessions = c.execute(
            "SELECT count(*) sessions FROM workouts "
            "WHERE user_id=%s AND performed_on=%s AND status='done'",
            (g.user_id, day),
        ).fetchone()["sessions"]
        week = week_summary(c, start)
        progress_end = min(day, date.today())
        progress = goal_progress(c, start, progress_end)
        recent = c.execute(
            "SELECT * FROM workouts WHERE user_id=%s ORDER BY performed_on DESC,created_at DESC LIMIT 5",
            (g.user_id,),
        ).fetchall()
        days = []
        for offset in range(7):
            current = start + timedelta(days=offset)
            total = c.execute(
                "SELECT COALESCE(sum(duration_min),0) minutes FROM workouts "
                "WHERE user_id=%s AND performed_on=%s AND status='done'",
                (g.user_id, current),
            ).fetchone()["minutes"]
            days.append({"date": iso(current), "minutes": int(total) if current <= date.today() else None})
        streak = streak_summary(c, g.user_id)
    return {
        "date": iso(day),
        "checkin": dict(log) if log else {"sleep_hours": None, "water_l": None},
        "today": {
            "minutes": sum(x["minutes"] or 0 for x in days if x["date"] == iso(day)),
            "sessions": int(today_sessions),
        },
        "week": week,
        "days": days,
        "streak": streak,
        "goal_progress": progress,
        "recent_workouts": [workout_json(row) for row in recent],
        "network_top": [],
        "network_note": "",
        "feed": [],
    }


@bp.get("/api/v1/workouts")
@auth_required
def list_workouts():
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("cursor", 0)), 0)
    except ValueError:
        return err("Invalid pagination.", "validation_error", 422)
    filters = ["user_id=%s"]
    params = [g.user_id]
    if request.args.get("sport"):
        filters.append("lower(sport_name)=lower(%s)")
        params.append(request.args["sport"])
    if request.args.get("status") in ("done", "planned"):
        filters.append("status=%s")
        params.append(request.args["status"])
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM workouts WHERE " + " AND ".join(filters) +
            " ORDER BY performed_on DESC,created_at DESC LIMIT %s OFFSET %s",
            (*params, limit + 1, offset),
        ).fetchall()
    return {"items": [workout_json(row) for row in rows[:limit]],
            "next_cursor": str(offset + limit) if len(rows) > limit else None}


@bp.post("/api/v1/workouts")
@auth_required
def create_workout():
    values = body()
    day = parse_date(values.get("performed_on"), date.today())
    if not values.get("sport") or not values.get("duration_min"):
        return err("Sport and duration are required.")
    try:
        duration = int(values["duration_min"])
    except (TypeError, ValueError):
        return err("Duration must be a number.", "validation_error", 422, "duration_min")
    if not day or duration < 1:
        return err("Workout date and duration are required.")
    with conn() as c:
        sport = c.execute(
            "SELECT id,name,met FROM sports WHERE id=%s OR lower(name)=lower(%s) LIMIT 1",
            (values.get("sport_id"), values["sport"]),
        ).fetchone()
        sport_id = sport["id"] if sport else values.get("sport_id")
        sport_name = sport["name"] if sport else values["sport"]
        met = float(sport["met"]) if sport else 6
        kcal = round(met * current_weight(c, g.user_id) * duration / 60)
        row = c.execute(
            "INSERT INTO workouts(user_id,sport_id,sport_name,title,performed_on,"
            "duration_min,distance_km,intensity,notes,kcal,status) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (g.user_id, sport_id, sport_name, values.get("title"), day, duration,
             values.get("distance_km"), values.get("intensity", "medium"),
             values.get("notes"), kcal, values.get("status", "done")),
        ).fetchone()
        c.commit()
        return {"workout": workout_json(row), "week": week_summary(c, day - timedelta(days=day.weekday()))}, 201


@bp.patch("/api/v1/workouts/<wid>")
@auth_required
def update_workout(wid):
    status = body().get("status")
    if status not in ("done", "planned"):
        return err("Status must be done or planned.")
    with conn() as c:
        row = c.execute(
            "UPDATE workouts SET status=%s WHERE id=%s AND user_id=%s RETURNING *",
            (status, wid, g.user_id),
        ).fetchone()
        if not row:
            return err("Workout not found.", "not_found", 404)
        c.commit()
        return {"workout": workout_json(row), "week": week_summary(c, date.today() - timedelta(days=date.today().weekday()))}


@bp.delete("/api/v1/workouts/<wid>")
@auth_required
def delete_workout(wid):
    with conn() as c:
        row = c.execute(
            "DELETE FROM workouts WHERE id=%s AND user_id=%s RETURNING id",
            (wid, g.user_id),
        ).fetchone()
        if not row:
            return err("Workout not found.", "not_found", 404)
        c.commit()
    return "", 204


@bp.get("/api/v1/workouts/stats")
@auth_required
def workout_stats():
    try:
        count = min(max(int(request.args.get("weeks", 8)), 1), 26)
    except ValueError:
        count = 8
    current = date.today() - timedelta(days=date.today().weekday())
    with conn() as c:
        weeks = []
        for offset in range(count - 1, -1, -1):
            start = current - timedelta(days=offset * 7)
            total = c.execute(
                "SELECT COALESCE(sum(duration_min),0) minutes FROM workouts "
                "WHERE user_id=%s AND performed_on BETWEEN %s AND %s AND status='done'",
                (g.user_id, start, start + timedelta(days=6)),
            ).fetchone()["minutes"]
            weeks.append({"week_start": iso(start), "minutes": int(total)})
        by_sport = c.execute(
            "SELECT sport_name sport,COALESCE(sum(duration_min),0) minutes "
            "FROM workouts WHERE user_id=%s AND performed_on BETWEEN %s AND %s "
            "AND status='done' GROUP BY sport_name ORDER BY minutes DESC",
            (g.user_id, current, current + timedelta(days=6)),
        ).fetchall()
        target = c.execute(
            "SELECT COALESCE(sum(minutes_per_session*sessions_per_week),0) target "
            "FROM activity_goals WHERE user_id=%s", (g.user_id,),
        ).fetchone()["target"] or 150
        progress = goal_progress(c, current, date.today())
        return {
            "weeks": weeks,
            "target_minutes": int(target),
            "week": week_summary(c, current, target),
            "by_sport": [dict(row) for row in by_sport],
            "goal_progress": progress,
            "personal_bests": personal_bests(c, g.user_id, weeks),
        }
