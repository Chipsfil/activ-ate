from datetime import date

from flask import Blueprint, g

from .common import auth_required, body, conn, current_weight, err, user_json

bp = Blueprint("profile", __name__)


def valid_sport_ids(c, sports):
    ids = {sport.get("sport_id") for sport in sports if sport.get("sport_id")}
    if not ids:
        return set()
    rows = c.execute(
        "SELECT id FROM sports WHERE id = ANY(%s)",
        (list(ids),),
    ).fetchall()
    return {row["id"] for row in rows}


@bp.get("/api/v1/me")
@auth_required
def me():
    with conn() as c:
        return user_json(c, g.user_id)


@bp.put("/api/v1/me/goals")
@auth_required
def save_goals():
    values = body()
    goals = values.get("goals", [])
    sports = values.get("sports", [])
    if not goals or not sports:
        return err("Choose at least one goal and one sport.")
    with conn() as c:
        sport_ids = valid_sport_ids(c, sports)
        c.execute("DELETE FROM user_goals WHERE user_id=%s", (g.user_id,))
        with c.cursor() as cur:
            cur.executemany(
                "INSERT INTO user_goals(user_id,goal,position) VALUES(%s,%s,%s)",
                [(g.user_id, goal, index) for index, goal in enumerate(goals)],
            )
        c.execute("DELETE FROM user_sports WHERE user_id=%s", (g.user_id,))
        with c.cursor() as cur:
            cur.executemany(
                "INSERT INTO user_sports(user_id,sport_id,name) VALUES(%s,%s,%s)",
                [(g.user_id, sport["sport_id"] if sport.get("sport_id") in sport_ids else None, sport["name"])
                 for sport in sports],
            )
        c.execute("UPDATE users SET onboarding_step='3' WHERE id=%s", (g.user_id,))
        c.commit()
    return {"goals": goals, "sports": sports}


@bp.get("/api/v1/me/targets")
@auth_required
def get_targets():
    with conn() as c:
        user_goals = c.execute(
            "SELECT goal FROM user_goals WHERE user_id=%s ORDER BY position",
            (g.user_id,),
        ).fetchall()
        user_sports = c.execute(
            "SELECT name,sport_id FROM user_sports WHERE user_id=%s ORDER BY name",
            (g.user_id,),
        ).fetchall()
        goals = c.execute(
            "SELECT id,sport_id,sport_name,minutes_per_session,sessions_per_week "
            "FROM activity_goals WHERE user_id=%s", (g.user_id,),
        ).fetchall()
        weight = current_weight(c, g.user_id)
    return {
        "goals": [row["goal"] for row in user_goals],
        "sports": [{"name": row["name"], "sport_id": row["sport_id"]} for row in user_sports],
        "activity_goals": [
            {"id": str(row["id"]), "sport": row["sport_name"], "sport_id": row["sport_id"],
             "minutes_per_session": row["minutes_per_session"],
             "sessions_per_week": row["sessions_per_week"]}
            for row in goals
        ],
        "nutrition_goals": [],
        "weight_goal": None,
        "current_weight_kg": weight,
    }


@bp.put("/api/v1/me/targets")
@auth_required
def save_targets():
    values = body()
    goals = values.get("activity_goals", [])
    if values.get("weight_goal") is not None:
        return err("Weight goals are not implemented yet.", "not_implemented", 501)
    if "current_weight_kg" in values:
        try:
            weight = float(values["current_weight_kg"])
        except (TypeError, ValueError):
            return err("Weight must be a number.", "validation_error", 422, "current_weight_kg")
        if not 30 <= weight <= 300:
            return err(
                "Weight must be between 30 and 300 kg.",
                "validation_error",
                422,
                "current_weight_kg",
            )
    with conn() as c:
        latest_weight = c.execute(
            "SELECT weight_kg FROM body_weights "
            "WHERE user_id=%s ORDER BY measured_on DESC LIMIT 1",
            (g.user_id,),
        ).fetchone()
        if (
            "current_weight_kg" in values
            and (
                latest_weight is None
                or weight != float(latest_weight["weight_kg"])
            )
        ):
            c.execute(
                "INSERT INTO body_weights(user_id,weight_kg,measured_on) "
                "VALUES(%s,%s,%s)",
                (g.user_id, weight, date.today()),
            )
        if "goals" in values and "sports" in values:
            sport_ids = valid_sport_ids(c, values["sports"])
            c.execute("DELETE FROM user_goals WHERE user_id=%s", (g.user_id,))
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO user_goals(user_id,goal,position) VALUES(%s,%s,%s)",
                    [(g.user_id, goal, index) for index, goal in enumerate(values["goals"])],
                )
            c.execute("DELETE FROM user_sports WHERE user_id=%s", (g.user_id,))
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO user_sports(user_id,sport_id,name) VALUES(%s,%s,%s)",
                    [(g.user_id, sport["sport_id"] if sport.get("sport_id") in sport_ids else None, sport["name"])
                     for sport in values["sports"]],
                )
        activity_sport_ids = valid_sport_ids(c, [
            {"sport_id": goal.get("sport_id")} for goal in goals
        ])
        c.execute("DELETE FROM activity_goals WHERE user_id=%s", (g.user_id,))
        with c.cursor() as cur:
            cur.executemany(
                "INSERT INTO activity_goals(user_id,sport_id,sport_name,minutes_per_session,sessions_per_week) "
                "VALUES(%s,%s,%s,%s,%s)",
                [(g.user_id, x["sport_id"] if x.get("sport_id") in activity_sport_ids else None,
                  x["sport"], x["minutes_per_session"], x["sessions_per_week"])
                 for x in goals],
            )
        c.execute(
            "UPDATE users SET onboarding_step='4' "
            "WHERE id=%s AND onboarding_step <> 'done'",
            (g.user_id,),
        )
        c.commit()
    return get_targets()


@bp.post("/api/v1/me/onboarding/complete")
@auth_required
def complete():
    with conn() as c:
        c.execute("UPDATE users SET onboarding_step='done' WHERE id=%s", (g.user_id,))
        c.commit()
    return {"network": {"id": "all-users", "member_count": 1}}


@bp.post("/api/v1/goals/check")
@auth_required
def goal_check():
    return {"checks": []}
