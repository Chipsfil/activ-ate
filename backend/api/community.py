from datetime import date, timedelta

from flask import Blueprint, g, request

from .common import auth_required, conn, err, iso

bp = Blueprint("community", __name__)


def _members(c, start=None, end=None):
    period = "AND w.performed_on BETWEEN %s AND %s" if start else ""
    params = [start, end] if start else []
    rows = c.execute(
        "SELECT u.id,u.first_name,u.last_name,"
        "COALESCE(SUM(w.duration_min),0) minutes "
        "FROM users u LEFT JOIN workouts w ON w.user_id=u.id "
        "AND w.status='done' " + period +
        "GROUP BY u.id,u.first_name,u.last_name ORDER BY minutes DESC,u.first_name",
        params,
    ).fetchall()
    return rows


@bp.get("/api/v1/community/network")
@auth_required
def network():
    with conn() as c:
        members = _members(c)
    return {
        "id": "all-users",
        "member_count": len(members),
        "criteria": ["All registered users"],
        "explanation": "This simple version puts all users in one network.",
        "shared_data": ["Exercise minutes", "Workout type and duration"],
    }


@bp.get("/api/v1/community/leaderboard")
@auth_required
def leaderboard():
    start = date.today() - timedelta(days=date.today().weekday())
    with conn() as c:
        rows = _members(c, start, start + timedelta(days=6))
    result = []
    for rank, row in enumerate(rows, 1):
        result.append({
            "member_id": str(row["id"]),
            "display_name": f"{row['first_name']} {row['last_name'][0]}.",
            "initials": (row["first_name"][0] + row["last_name"][0]).upper(),
            "is_me": str(row["id"]) == str(g.user_id),
            "value": int(row["minutes"]),
            "rank": rank,
        })
    return {
        "habit": request.args.get("habit", "exercise"),
        "unit": "min",
        "period": "week",
        "target_label": "Weekly target",
        "rows": result,
        "summary": {
            "my_rank": next((x["rank"] for x in result if x["is_me"]), None),
            "member_count": len(result),
        },
    }


@bp.get("/api/v1/community/members/<mid>")
@auth_required
def member(mid):
    start = date.today() - timedelta(days=date.today().weekday())
    with conn() as c:
        row = c.execute("SELECT id,first_name,last_name FROM users WHERE id=%s", (mid,)).fetchone()
        if not row: return err("Member not found.", "not_found", 404)
        history = c.execute(
            "SELECT performed_on,COALESCE(SUM(duration_min),0) minutes "
            "FROM workouts WHERE user_id=%s AND status='done' "
            "GROUP BY performed_on ORDER BY performed_on DESC LIMIT 30", (mid,),
        ).fetchall()
    return {
        "member": {
            "id": str(row["id"]),
            "display_name": f"{row['first_name']} {row['last_name'][0]}.",
            "initials": (row["first_name"][0] + row["last_name"][0]).upper(),
        },
        "history": [{"date": iso(x["performed_on"]), "minutes": int(x["minutes"])} for x in history],
        "week_start": iso(start),
    }


@bp.post("/api/v1/community/members/<mid>/cheers")
@auth_required
def cheer(mid):
    return {"message": "Cheers are not enabled in the simple backend."}, 200


@bp.get("/api/v1/community/insights")
@auth_required
def insights():
    with conn() as c:
        rows = _members(c)
    return {"habit": request.args.get("habit", "exercise"), "items": [
        {"member_id": str(x["id"]), "minutes": int(x["minutes"])}
        for x in rows[:5]
    ]}


@bp.get("/api/v1/feed")
@auth_required
def feed():
    return {"items": []}
