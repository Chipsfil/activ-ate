from flask import Blueprint, g

from .common import (
    auth_required,
    body,
    conn,
    current_weight,
    err,
    iso,
    user_json,
)

bp = Blueprint("profile", __name__)

@bp.get("/api/v1/me")
@auth_required
def me():
    with conn() as c: return user_json(c,g.user_id)

@bp.put("/api/v1/me/goals")
@auth_required
def save_goals():
    b=body(); goals=b.get("goals",[]); sports=b.get("sports",[])
    if not goals or not sports: return err("Choose at least one goal and one sport.")
    with conn() as c:
        c.execute("DELETE FROM user_goals WHERE user_id=%s",(g.user_id,))
        with c.cursor() as cur:
            cur.executemany("INSERT INTO user_goals(user_id,goal,position) VALUES(%s,%s,%s)",[(g.user_id,x,i) for i,x in enumerate(goals)])
        c.execute("DELETE FROM user_sports WHERE user_id=%s",(g.user_id,))
        with c.cursor() as cur:
            cur.executemany("INSERT INTO user_sports(user_id,sport_id,name) VALUES(%s,%s,%s)",[(g.user_id,x.get("sport_id"),x["name"]) for x in sports])
        c.execute("UPDATE users SET onboarding_step='3' WHERE id=%s",(g.user_id,)); c.commit()
    return {"goals":goals,"sports":sports}

def targets(c,uid):
    goals=[r["goal"] for r in c.execute("SELECT goal FROM user_goals WHERE user_id=%s ORDER BY position",(uid,))]
    sports=[dict(name=r["name"],sport_id=r["sport_id"]) for r in c.execute("SELECT name,sport_id FROM user_sports WHERE user_id=%s",(uid,))]
    ag=[{"id":str(r["id"]),"sport":r["sport_name"],"sport_id":r["sport_id"],"minutes_per_session":r["minutes_per_session"],"sessions_per_week":r["sessions_per_week"]} for r in c.execute("SELECT * FROM activity_goals WHERE user_id=%s",(uid,))]
    ng=[{"nutrient":r["nutrient"],"amount":float(r["amount"])} for r in c.execute("SELECT * FROM nutrition_goals WHERE user_id=%s",(uid,))]
    wg=c.execute("SELECT * FROM weight_goals WHERE user_id=%s",(uid,)).fetchone()
    return {"goals":goals,"sports":sports,"activity_goals":ag,"nutrition_goals":ng,"sleep_goal_h":float(c.execute("SELECT sleep_goal_h FROM users WHERE id=%s",(uid,)).fetchone()["sleep_goal_h"]),"weight_goal":({"start_kg":float(wg["start_kg"]) if wg["start_kg"] else None,"target_kg":float(wg["target_kg"]),"target_date":iso(wg["target_date"])} if wg else None),"current_weight_kg":current_weight(c,uid),"computed_defaults":{"kcal":2350,"protein_g":round(current_weight(c,uid)*1.8)}}
@bp.get("/api/v1/me/targets")
@auth_required
def get_targets():
    with conn() as c:return targets(c,g.user_id)
@bp.put("/api/v1/me/targets")
@auth_required
def put_targets():
    b=body()
    with conn() as c:
        if "activity_goals" in b:
            c.execute("DELETE FROM activity_goals WHERE user_id=%s",(g.user_id,))
            with c.cursor() as cur:
                cur.executemany("INSERT INTO activity_goals(user_id,sport_id,sport_name,minutes_per_session,sessions_per_week) VALUES(%s,%s,%s,%s,%s)",[(g.user_id,x.get("sport_id"),x["sport"],x["minutes_per_session"],x["sessions_per_week"]) for x in b["activity_goals"]])
        if "nutrition_goals" in b:
            c.execute("DELETE FROM nutrition_goals WHERE user_id=%s",(g.user_id,))
            with c.cursor() as cur:
                cur.executemany("INSERT INTO nutrition_goals(user_id,nutrient,amount) VALUES(%s,%s,%s)",[(g.user_id,x["nutrient"],x["amount"]) for x in b["nutrition_goals"]])
        if "sleep_goal_h" in b:c.execute("UPDATE users SET sleep_goal_h=%s WHERE id=%s",(b["sleep_goal_h"],g.user_id))
        if "current_weight_kg" in b:c.execute("INSERT INTO body_weights(user_id,weight_kg,measured_on) VALUES(%s,%s,current_date)",(g.user_id,b["current_weight_kg"]))
        if "weight_goal" in b:
            c.execute("DELETE FROM weight_goals WHERE user_id=%s",(g.user_id,))
            if b["weight_goal"]: c.execute("INSERT INTO weight_goals(user_id,start_kg,target_kg,target_date) VALUES(%s,%s,%s,%s)",(g.user_id,current_weight(c,g.user_id),b["weight_goal"]["target_kg"],b["weight_goal"]["target_date"]))
        c.execute("UPDATE users SET onboarding_step='4' WHERE id=%s",(g.user_id,)); c.commit(); return targets(c,g.user_id)
@bp.post("/api/v1/me/onboarding/complete")
@auth_required
def complete(): 
    with conn() as c:
        c.execute("UPDATE users SET onboarding_step='done' WHERE id=%s",(g.user_id,)); c.commit()
        return {"network":{"id":None,"member_count":1,"criteria":[]}}

@bp.post("/api/v1/goals/check")
@auth_required
def goal_check():
    return {"checks":[]}
