# Speedy Dismissal

A QR-code-based school dismissal and pickup system built with Flask. Guardians are issued a QR token; scanning it at pickup instantly notifies the right teacher's dashboard in real time via WebSockets, and the front-office "logs" view tracks every request from scan to student release.

## How it works

1. Each guardian is assigned a unique QR token.
2. At pickup, staff scan the guardian's QR code using the **Scanner** page (in-browser camera scanner).
3. The scan looks up which student(s) are linked to that guardian and creates a pickup request.
4. The student's teacher sees the request appear live on their **Dashboard** (via Socket.IO), organized by classroom group.
5. The teacher marks the student as sent; that update is broadcast live to the **Logs** page used at the pickup/door area.
6. An **Admin** page provides full CRUD over students, groups, guardians, users, and tokens.

## Roles

Access is controlled by session-based login with four roles:

| Role      | Landing page   | Purpose                                              |
|-----------|----------------|-------------------------------------------------------|
| `TEACHER` | `/dashboard`   | View pending/sent pickups for their own group         |
| `SCANNER` | `/scanner`     | Scan guardian QR codes to initiate pickup requests     |
| `DOOR`    | `/logs`        | View live pending/sent pickup logs at the pickup point |
| `ADMIN`   | `/admin`       | Manage students, groups, guardians, users, and tokens; also has scanner/logs access |

## Tech stack

- **Backend:** Flask, Flask-SocketIO (real-time updates), Flask-Session
- **Database:** SQLite, accessed via CS50's `SQL` wrapper (see `dismissal.sql` for schema)
- **Real-time:** Socket.IO rooms — one room per classroom group, plus a shared `logs` room
- **Frontend:** Server-rendered Jinja templates, [html5-qrcode](https://github.com/mebjas/html5-qrcode) for in-browser QR scanning
- **PWA:** Includes a manifest and service worker so the app can be installed on a phone/tablet for use as a scanner station

## Project structure

```
app.py                  # Flask app: routes, auth, Socket.IO events, generic CRUD endpoints
helpers.py               # login_required / role_required decorators, apology() error page
dismissal.sql             # Database schema (groups, students, guardians, tokens, users, pickups, ...)
templates/
  layout.html              # Base layout
  login.html                # Login form
  index.html                 # Teacher dashboard
  scanner.html                # QR scanner page
  logs.html                    # Live pickup log (pending/sent)
  admin.html                    # Admin CRUD console
  apology.html                   # Generic error page
static/
  styles.css               # App styling
  manifest.json, icons/, service-worker.js   # PWA assets
```

## Database schema

Defined in `dismissal.sql`:

- **groups** — classrooms/teacher groups
- **students** — linked to a group
- **guardians** — parents/guardians authorized for pickup
- **guardian_students** — many-to-many link between guardians and students
- **tokens** — QR token values issued to guardians
- **users** — login accounts (`ADMIN`, `SCANNER`, `TEACHER`, `DOOR`)
- **pickups** — one row per QR scan/pickup request
- **pickup_students** — students included in a given pickup (supports sibling groups), with per-student `PENDING`/`SENT` status

## Setup

1. **Clone and enter the repo**
   ```bash
   git clone <repo-url>
   cd SpeedyDismissal
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create the database**
   ```bash
   sqlite3 dismissal.db < dismissal.sql
   ```

4. **Create at least one user** (e.g. an admin) so you can log in — either via `sqlite3 dismissal.db` directly, or by seeding one manually with a `werkzeug.security.generate_password_hash` password hash.

5. **Run the app**
   ```bash
   python app.py
   ```
   The app starts on `http://127.0.0.1:5000` using `eventlet` as the Socket.IO async server.
