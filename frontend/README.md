# Activ-Ate – Frontend

Health web app: log workouts and meals, get AI recommendations, and compare yourself with an automatically
assigned network of similar people. This repository contains the **complete frontend** (plain HTML, CSS and
JavaScript – no build step) plus the **documentation the backend team needs**.

The backend (Python + PostgreSQL + Claude/OpenAI API) is **not built yet**. Until then a mock backend runs inside the
browser, so every page already works end to end (data is stored in `localStorage`).

| Document | For whom | Content |
| --- | --- | --- |
| [docs/API.md](docs/API.md) | Backend developer | Every endpoint with request/response JSON, validation and errors |
| [docs/BACKEND.md](docs/BACKEND.md) | Backend developer | Architecture, database tables, business rules, network assignment, AI prompts, security |
| [deploy/](deploy/) | Whoever deploys | nginx config + setup script for a Google Cloud VM |

---

## Run locally (2 minutes)

ES modules do not work from `file://`, so start any static web server in the project folder:

```bash
cd activ-ate-frontend
python3 -m http.server 8080
# open http://localhost:8080
```

**Demo login (mock mode):** username `demo`, password `demo1234` – 8 weeks of example data.
Or create a new account through the onboarding. To reset all demo data run in the browser console:
`localStorage.clear()`.

---

## Pages

| Page | File | Main endpoints |
| --- | --- | --- |
| Entry (redirect) | `index.html` | `POST /auth/refresh` |
| Sign in | `signin.html` | `POST /auth/login` |
| Forgot / reset password | `forgot-password.html`, `reset-password.html` | `POST /auth/password-reset`, `…/confirm` |
| Sign up (3-step onboarding) | `signup.html` | `POST /auth/register`, `PUT /me/goals`, `PUT /me/targets`, `POST /me/onboarding/complete` |
| Dashboard | `dashboard.html` | `GET /dashboard`, `GET /recommendations/daily`, `PUT /daily-logs`, `POST /workouts` |
| Workouts | `workouts.html` | `GET /workouts`, `GET /workouts/stats`, `POST/PATCH/DELETE /workouts` |
| Nutrition | `nutrition.html` | `POST /meals/estimate`, `POST /meals`, `GET /nutrition/summary` |
| Goals | `goals.html` | `GET/PUT /me/targets`, `POST /goals/check` |
| Community | `community.html` | `GET /community/leaderboard`, `POST …/cheers`, `GET /community/insights` |
| Network member | `member.html?id=…` | `GET /community/members/{id}` |
| AI Coach | `coach.html` | `POST /coach/messages` |

### What changed compared to the clickable prototype
- **Community = automatic network.** Users are matched by height, weight, age and main goal. No "add friend", no friend requests, no messaging. The only interaction is **cheering** a member who reached a goal.
- **No "share your data" step** in onboarding. Exercise minutes, workouts, streaks, sleep and water are shared with the network automatically; meals and body weight stay private (shown to the user in onboarding and on the Goals page).
- **Sports are typed with autocomplete** (onboarding, goals, workout logging). Users can also keep their own text if a sport is not in the list. The list comes from `GET /sports` – later ~1000 sports with calories per minute; seed data in `assets/data/sports.json`.
- **Daily check-in** for sleep and water on the dashboard (needed for the sleep/water comparison).
- Onboarding has 3 steps: About you → Goals & sports → Targets.

---

## Project structure

```
index.html, signin.html, signup.html, …   one HTML file per page (layout only)
assets/css/styles.css                      design system (colours, type, components, responsive)
assets/js/config.js                        API URL + mock switch
assets/js/api.js                           the ONLY place that talks to the backend (fetch, tokens, errors)
assets/js/ui.js                            sidebar, auth guard, toasts, formatting, escaping
assets/js/components/                      sport autocomplete, workout form
assets/js/pages/*.js                       one script per page
assets/js/mock/                            in-browser mock backend (delete when the real API is live)
assets/data/sports.json                    seed list of sports with MET values
docs/                                      API contract + backend specification
deploy/                                    nginx config + VM setup script
```

Conventions: all text from users or the backend is escaped with `esc()` before it is put into HTML; every form shows
backend validation errors under the field named in the error response; buttons show a spinner while a request runs.

---

## Deploy on a Google Cloud VM

Prerequisites: a Google Cloud project with billing and the `gcloud` CLI (or use the Cloud Console and its SSH button).

```bash
# 1. Create a small VM (Zurich region) and allow HTTP/HTTPS
gcloud compute instances create activ-ate-web \
  --zone=europe-west6-a --machine-type=e2-small \
  --image-family=debian-12 --image-project=debian-cloud \
  --tags=http-server,https-server
gcloud compute firewall-rules create allow-web --allow=tcp:80,tcp:443 --target-tags=http-server,https-server
#    (skip the firewall command if the rule already exists in your project)

# 2. Copy the project to the VM
zip -r activ-ate-frontend.zip activ-ate-frontend
gcloud compute scp activ-ate-frontend.zip activ-ate-web:~ --zone=europe-west6-a

# 3. Install on the VM
gcloud compute ssh activ-ate-web --zone=europe-west6-a
sudo apt-get install -y unzip && unzip -o activ-ate-frontend.zip && cd activ-ate-frontend
sudo bash deploy/setup-vm.sh                                   # http://<external-ip>/
# with a domain pointing to the VM's IP, also get HTTPS:
sudo bash deploy/setup-vm.sh activ-ate.example.com you@example.com
```

Updating later: copy the new zip, unzip, run `sudo bash deploy/setup-vm.sh` again (it syncs the files and reloads nginx).

Notes:
- An `e2-micro` VM is in Google's free tier only in some US regions (`us-west1`, `us-central1`, `us-east1`); in Zurich use `e2-small` (small monthly cost). Check current prices in the Google Cloud pricing calculator.
- In mock mode each visitor has their own data in their own browser – fine for demos, not a real multi-user app.
- When the backend runs on the same VM (FastAPI on `127.0.0.1:8000`), uncomment the `location /api/` block in `deploy/nginx.conf`, set `USE_MOCK_API: false` in `assets/js/config.js` and run the setup script again. See docs/BACKEND.md §8.
