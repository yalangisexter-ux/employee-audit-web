# Employee Audit Manager — Independent Web App

Standalone web application for **Raw Strength Calisthenics — Employee Audit Manager**.

This repository is independent of the Windows desktop EXE, installer, updater, and the `yalangisexter-ux/audit-report` repository. Do not use this web deployment to modify desktop releases.

## Current modules

- Secure username/password authentication (case-sensitive usernames)
- Dashboard KPIs
- Employees, tasks, and attendance
- Business tracking: products, services, orders, members, activities
- Customer / prospect directory
- Print center (browser print / Save as PDF)
- Settings and database status
- Responsive desktop and mobile navigation

The web SPA includes dashboard, employee/task/attendance workflows, operational modules, EOD, store directory, print/CSV, account password changes, backups, and encrypted EXE/mobile Cloud Sync. Full parity with every desktop workflow still requires acceptance testing against a real desktop export.

## Security and first account

The web application has its own independent database and account system. It does **not** import, migrate, or reuse Windows EXE users, passwords, or business records.

On a brand-new empty web database, open the web URL and the application displays **Create your web administrator**. Create the first username and password there (minimum 12 characters). This one-time setup endpoint is disabled automatically after the first account is created. There are no built-in or default credentials.

After setup, sign in with the new web account. Use Settings to change your password; an administrator can reset another web user's password. Usernames are case-sensitive. Keep `WEB_SESSION_SECRET` stable across restarts (at least 32 characters) for hosted deployments. Generate it with `python -c 'import secrets; print(secrets.token_urlsafe(48))'` and store it as a hosting secret.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export WEB_ADMIN_PASSWORD='replace-with-a-unique-password'\nexport WEB_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000.

## Free hosting: Render

A free Render Web Service can run this FastAPI application, but its filesystem is ephemeral. **The current SQLite database is not safe for real customer records on Render Free**: records can be lost when the service sleeps, restarts, or redeploys. Render's persistent disks require a paid service, and its free Render Postgres databases expire after 30 days.

For a no-cost demonstration, connect this repository to Render as a Web Service using the included `render.yaml`, then set the administrator environment variables above. Do not enter real business/customer data until a persistent external database (for example, a free-tier managed PostgreSQL provider) is integrated and verified.

Render setup:
1. Create a new Web Service and connect this repository.
2. Use the Blueprint from `render.yaml`, or set the build command to `pip install -r requirements.txt`.
3. Set the start command to `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
4. Add `WEB_BOOTSTRAP_USERS=true`, administrator credentials, and `WEB_SESSION_SECRET` as secret environment variables.
5. Verify `/api/health` and login before sharing the URL.

Free Render services sleep after inactivity and may take around a minute to wake. See [Render free instance limits](https://render.com/docs/free).

## API

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard`
- CRUD routes under `/api/employees`, `/api/tasks`, `/api/attendance`, `/api/business/*`, and `/api/customers`
- `GET /api/health`

