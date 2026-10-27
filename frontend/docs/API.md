# Activ-Ate API (v1)

This document describes the Flask API currently implemented in `../../backend`.
All routes use `/api/v1`. The frontend calls it through `assets/js/api.js`;
mock mode is implemented separately in `assets/js/mock/` and may differ.

## Conventions

- Send and receive JSON, except `204 No Content` responses.
- Protected routes require `Authorization: Bearer <access_token>`.
- Registration and login return an access token and set an HttpOnly
  `refresh_token` cookie. `POST /auth/refresh` rotates the cookie and returns a
  new access token. `POST /auth/logout` revokes it.
- Errors use `{ "error": "…", "message": "…", "field": "…" }`; `field` is
  optional. Validation errors generally use HTTP 422.
- Dates use `YYYY-MM-DD`; measurements use metric units.

## Authentication and profile

| Method and path | Access | Current behavior |
| --- | --- | --- |
| `GET /auth/username-available?username=…` | Public | Returns `{ available }`; names shorter than 3 characters return `available: false` and `reason: "too_short"`. |
| `POST /auth/register` | Public | Requires name, username, email, password, gender, birth date, weight, and height. Password must be at least 8 characters. Creates the user and starting weight; returns `{ access_token, user }` with status 201. |
| `POST /auth/login` | Public | Accepts username or email and password. Returns `{ access_token, user }`; invalid credentials return 401. |
| `POST /auth/refresh` | Public, cookie | Rotates a valid refresh session and returns `{ access_token, user }`; otherwise 401. |
| `POST /auth/logout` | Public, cookie | Revokes the refresh session and returns 204. |
| `GET /me` | Authenticated | Returns the user profile, goals, sports, and current weight. |
| `PUT /me/goals` | Authenticated | Accepts `goals` and `sports`; both must be non-empty. Replaces them and advances onboarding. |
| `GET /me/targets` | Authenticated | Returns activity goals and current weight. Nutrition goals are empty and `weight_goal` is null. |
| `PUT /me/targets` | Authenticated | Replaces `activity_goals`; may update `current_weight_kg` (30–300). Weight goals return 501. |
| `POST /me/onboarding/complete` | Authenticated | Marks onboarding complete; returns the shared `all-users` network summary. |
| `POST /goals/check` | Authenticated | Currently returns `{ checks: [] }`. |

`User` includes `id`, `username`, `email`, `first_name`, `last_name`,
`initials`, `gender`, `date_of_birth`, `height_cm`, `onboarding_step`, `goals`,
`sports`, `current_weight_kg`, and `created_at`. A sport is
`{ "name": "Running", "sport_id": "running" }`; custom names may use a null
`sport_id`.

## Sports and activity

| Method and path | Access | Current behavior |
| --- | --- | --- |
| `GET /sports?q=run&limit=8` | Public | Searches the PostgreSQL sports catalog by name or alias. Limit is clamped to 1–50. Returns `{ items: [{ id, name, category, met }] }`. |
| `GET /dashboard?date=YYYY-MM-DD` | Authenticated | Returns selected date, check-in, today totals, week totals, daily minutes, streak, activity goal progress, and recent workouts. `network_top` and `feed` are empty. |
| `PUT /daily-logs` | Authenticated | Upserts `{ date, sleep_hours, water_l }`; returns the saved date and values. |
| `GET /workouts?limit=20&cursor=0&sport=…&status=done` | Authenticated | Lists the user's workouts, newest first. `cursor` is an offset; response is `{ items, next_cursor }`. |
| `POST /workouts` | Authenticated | Requires `sport` and `duration_min`; optional fields include `sport_id`, `title`, `performed_on`, `distance_km`, `intensity`, `notes`, and `status`. Returns `{ workout, week }` with status 201. Calories are estimated from MET and current weight. |
| `PATCH /workouts/{id}` | Authenticated | Accepts `{ "status": "done" }` or `{ "status": "planned" }`; returns `{ workout, week }`. |
| `DELETE /workouts/{id}` | Authenticated | Deletes the user's workout; returns 204. Missing or unowned IDs return 404. |
| `GET /workouts/stats?weeks=8` | Authenticated | Returns weekly minutes, target, current week summary, minutes by sport, goal progress, and personal bests. Weeks are clamped to 1–26. |

A workout contains `id`, `sport`, `sport_id`, `title`, `performed_on`,
`duration_min`, `distance_km`, `intensity`, `notes`, `kcal`, `status`, and
`created_at`. Weekly targets default to 150 minutes when no activity goals are
saved.

## Nutrition, recommendations, community, and coach

| Method and path | Access | Current behavior |
| --- | --- | --- |
| `GET /nutrition/summary` | Authenticated | Placeholder; returns HTTP 501. |
| `GET /meals`, `POST /meals` | Authenticated | Placeholder; returns HTTP 501. |
| `POST /meals/estimate` | Authenticated | Placeholder; returns HTTP 501. |
| `DELETE /meals/{id}` | Authenticated | Placeholder; returns HTTP 501. |
| `GET /recommendations/daily` | Authenticated | Fixed fallback text; `suggested_session` is null. No AI generation. |
| `GET /recommendations/workout` | Authenticated | Fixed fallback text and an empty `tips` array. |
| `GET /recommendations/nutrition` | Authenticated | Fixed fallback text and empty `more_of` and `watch` arrays. |
| `GET /community/network` | Authenticated | All registered users share one network. Only exercise data is supported. |
| `GET /community/leaderboard?habit=exercise` | Authenticated | Weekly exercise minutes, streaks, ranks, and cheer eligibility for all users. Other habits return 422. |
| `GET /community/members/{id}?period=week` | Authenticated | Returns a member's exercise totals and recent completed workouts. Period can be `week`, `month`, or `all`; other habits return 422. |
| `POST /community/members/{id}/cheers` | Authenticated | Accepts `{ "habit": "exercise" }`; requires the member to meet their weekly target. One cheer per member per week; returns 201. |
| `GET /community/insights?habit=exercise` | Authenticated | Rule-based exercise messages, not AI-generated. |
| `GET /feed?limit=10` | Authenticated | Lists members who reached their weekly exercise target. |
| `GET /coach/context` | Authenticated | Returns the user's name, selected sports, and weekly activity target. |
| `GET /coach/conversations/latest` | Authenticated | Returns `{ conversation_id: null, messages: [] }`; conversations are not persisted. |
| `POST /coach/conversations` | Authenticated | Returns a new conversation ID and empty messages; not persisted. |
| `POST /coach/messages` | Authenticated | Returns a fixed reply for a few suggested prompts, otherwise a generic prompt. No AI call or message persistence. |
| `GET /health` | Public | Checks database connectivity; returns `{ status: "ok", database: "ok" }` or 503. |

For setup and configuration, see [`../../backend/README.md`](../../backend/README.md).
