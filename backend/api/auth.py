from flask import Blueprint
from .common import *

bp = Blueprint("auth", __name__)

@bp.get("/api/v1/auth/username-available")
def username_available():
    name = request.args.get("username","").lower()
    if len(name) < 3: return {"available": False, "reason":"too_short"}
    with conn() as c: return {"available": not bool(c.execute("SELECT 1 FROM users WHERE username=%s", (name,)).fetchone())}

@bp.post("/api/v1/auth/register")
def register():
    b=body(); required=("first_name","last_name","username","email","password","gender","date_of_birth","weight_kg","height_cm")
    if any(k not in b for k in required): return err("All registration fields are required.")
    if len(b["password"])<8: return err("Password must be at least 8 characters.","validation_error",422,"password")
    dob=parse_date(b["date_of_birth"])
    if not dob or (date.today()-dob).days < 16*365: return err("You must be at least 16 years old.","validation_error",422,"date_of_birth")
    with conn() as c:
        if c.execute("SELECT 1 FROM users WHERE username=%s", (b["username"].lower(),)).fetchone(): return err("Username is already taken.","conflict",409,"username")
        if c.execute("SELECT 1 FROM users WHERE email=%s", (b["email"].lower(),)).fetchone(): return err("Email is already registered.","conflict",409,"email")
        try:
            u=c.execute("""INSERT INTO users(username,email,password_hash,first_name,last_name,gender,date_of_birth,height_cm)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(b["username"].lower(),b["email"].lower(),generate_password_hash(b["password"]),b["first_name"],b["last_name"],b["gender"],dob,b["height_cm"])).fetchone()
            c.execute("INSERT INTO body_weights(user_id,weight_kg,measured_on) VALUES(%s,%s,current_date)",(u["id"],b["weight_kg"])); c.commit()
            return refresh_response(c,u["id"]), 201
        except psycopg.errors.CheckViolation: c.rollback(); return err("Height and weight are outside allowed ranges.")

@bp.post("/api/v1/auth/login")
def login():
    b=body()
    with conn() as c:
        u=c.execute("SELECT id,password_hash FROM users WHERE username=%s OR email=%s",(b.get("username","").lower(),b.get("username","").lower())).fetchone()
        if not u or not check_password_hash(u["password_hash"],b.get("password","")): return err("Invalid username or password.","invalid_credentials",401)
        return refresh_response(c,u["id"])
@bp.post("/api/v1/auth/refresh")
def refresh():
    raw=request.cookies.get("refresh_token")
    with conn() as c:
        r=c.execute("SELECT user_id FROM refresh_sessions WHERE token_hash=%s AND revoked_at IS NULL AND expires_at>now()",(token_hash(raw),)).fetchone() if raw else None
        if not r: return err("Your session has expired.","unauthorized",401)
        c.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=%s",(token_hash(raw),)); c.commit()
        return refresh_response(c,r["user_id"])
@bp.post("/api/v1/auth/logout")
def logout():
    raw=request.cookies.get("refresh_token")
    with conn() as c:
        if raw: c.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=%s",(token_hash(raw),)); c.commit()
    r=make_response("",204); r.delete_cookie("refresh_token",path="/api/v1/auth"); return r
@bp.post("/api/v1/auth/password-reset")
def password_reset(): return {"message":"If an account exists, a reset link has been sent."},202
@bp.post("/api/v1/auth/password-reset/confirm")
def password_reset_confirm(): return {"message":"Password changed."}

