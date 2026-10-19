"""Shared helpers for the Activ-Ate API."""
from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from functools import wraps

import jwt
import psycopg
from flask import g, jsonify, make_response, request
from config import COOKIE_SAMESITE, COOKIE_SECURE, DATABASE_URL, JWT_SECRET

DB = DATABASE_URL
SECRET = JWT_SECRET


def conn():
    return psycopg.connect(DB, row_factory=psycopg.rows.dict_row)


def err(message, code="validation_error", status=422, field=None):
    response = {"error": code, "message": message}
    if field:
        response["field"] = field
    return jsonify(response), status


def body():
    return request.get_json(silent=True) or {}


def iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def access_token(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def user_json(c, uid):
    u = c.execute("SELECT * FROM users WHERE id=%s", (uid,)).fetchone()
    goal_rows = c.execute(
        "SELECT goal FROM user_goals WHERE user_id=%s ORDER BY position",
        (uid,),
    )
    goals = [row["goal"] for row in goal_rows]

    sport_rows = c.execute(
        "SELECT name,sport_id FROM user_sports WHERE user_id=%s ORDER BY name",
        (uid,),
    )
    sports = [
        {"name": row["name"], "sport_id": row["sport_id"]}
        for row in sport_rows
    ]

    weight = c.execute(
        "SELECT weight_kg FROM body_weights "
        "WHERE user_id=%s ORDER BY measured_on DESC LIMIT 1",
        (uid,),
    ).fetchone()

    return {
        "id": str(u["id"]),
        "username": u["username"],
        "email": u["email"],
        "first_name": u["first_name"],
        "last_name": u["last_name"],
        "initials": (u["first_name"][0] + u["last_name"][0]).upper(),
        "gender": u["gender"],
        "date_of_birth": iso(u["date_of_birth"]),
        "height_cm": float(u["height_cm"]),
        "onboarding_step": u["onboarding_step"],
        "goals": goals,
        "sports": sports,
        "current_weight_kg": float(weight["weight_kg"]) if weight else None,
        "created_at": u["created_at"].isoformat(),
    }


def auth_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        raw = request.headers.get("Authorization", "")
        if not raw.startswith("Bearer "):
            return err("Authentication is required.", "unauthorized", 401)

        try:
            uid = jwt.decode(raw[7:], SECRET, algorithms=["HS256"])["sub"]
        except (jwt.InvalidTokenError, KeyError):
            return err("Your session has expired.", "unauthorized", 401)

        with conn() as c:
            user_exists = c.execute(
                "SELECT 1 FROM users WHERE id=%s", (uid,)
            ).fetchone()
            if not user_exists:
                return err("User not found.", "unauthorized", 401)

        g.user_id = uid
        return fn(*a, **kw)

    return wrapped


def refresh_response(c, uid):
    raw = secrets.token_urlsafe(48)
    c.execute(
        "INSERT INTO refresh_sessions(user_id,token_hash,expires_at) "
        "VALUES(%s,%s,%s)",
        (
            uid,
            token_hash(raw),
            datetime.now(timezone.utc) + timedelta(days=30),
        ),
    )

    response = make_response(
        jsonify({"access_token": access_token(uid), "user": user_json(c, uid)})
    )
    response.set_cookie(
        "refresh_token",
        raw,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/api/v1/auth",
        max_age=2592000,
    )
    return response


def parse_date(v, default=None):
    try:
        if v:
            return date.fromisoformat(v)
        return default
    except (TypeError, ValueError):
        return None


def current_weight(c, uid):
    row = c.execute(
        "SELECT weight_kg FROM body_weights "
        "WHERE user_id=%s ORDER BY measured_on DESC LIMIT 1",
        (uid,),
    ).fetchone()
    if row:
        return float(row["weight_kg"])
    return 70.0


def sport(c, sid, name):
    row = c.execute(
        "SELECT id,name,met FROM sports "
        "WHERE id=%s OR lower(name)=lower(%s) LIMIT 1",
        (sid, name),
    ).fetchone()
    if row:
        return row
    return {"id": sid, "name": name, "met": 6.0}


def totals(c, uid, d):
    row = c.execute(
        "SELECT COALESCE(sum(kcal),0) kcal, "
        "COALESCE(sum(protein_g),0) protein_g, "
        "COALESCE(sum(carbs_g),0) carbs_g, "
        "COALESCE(sum(fat_g),0) fat_g "
        "FROM meals WHERE user_id=%s AND eaten_on=%s",
        (uid, d),
    ).fetchone()
    return {
        "kcal": float(row["kcal"]),
        "protein_g": float(row["protein_g"]),
        "carbs_g": float(row["carbs_g"]),
        "fat_g": float(row["fat_g"]),
    }


def placeholder(name, value=None):
    @auth_required
    def view():
        if value is not None:
            return value
        return {"items": []}

    view.__name__ = name
    return view
