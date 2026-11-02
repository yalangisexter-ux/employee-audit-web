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

**Important:** This is not yet full desktop-EXE parity. Several modules currently have create/delete rather than complete edit workflows. Validate every workflow before production use.

## Security and first account

There are **no default usernames or passwords** in the source code. Previous sample credentials have been removed; treat any credentials previously published in this repository as compromised and do not reuse them.

For a hosted instance, set these environment variables in the hosting provider's secret/environment settings:

| Variable | Required | Description |
|---|---:|---|
| `WEB_BOOTSTRAP_USERS` | Yes | Set to `true` to provision the administrator from secrets |
| `WEB_ADMIN_USERNAME` | Yes | Your chosen case-sensitive admin username |
| `WEB_ADMIN_PASSWORD` | Yes | Unique password, minimum 12 characters |
| `WEB_ADMIN_DISPLAY_NAME` | No | Display name |\n| `WEB_SESSION_SECRET` | Strongly recommended | Stable random secret (at least 32 characters) used to sign restart-safe login sessions |
| `WEB_DEVELOPER_USERNAME` | No | Optional separate developer username |
| `WEB_DEVELOPER_PASSWORD` | No | Optional separate developer password, minimum 12 characters |

If developer credentials are configured, set both developer variables. Bootstrap credentials are applied to the named accounts at startup, allowing an operator to rotate them by changing the provider secrets. Never commit secret values. Generate a stable session secret once with `python -c 'import secrets; print(secrets.token_urlsafe(48))'` and save it as `WEB_SESSION_SECRET` in Light Cloud environment secrets. Do not regenerate it during normal deploys. If the host uses ephemeral storage, this secret must be configured.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export WEB_BOOTSTRAP_USERS=true
export WEB_ADMIN_USERNAME=Admin
export WEB_ADMIN_PASSWORD='replace-with-a-unique-password'
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
4. Add the administrator credentials as secret environment variables.
5. Verify `/api/health` and login before sharing the URL.

Free Render services sleep after inactivity and may take around a minute to wake. See [Render free instance limits](https://render.com/docs/free).

## API

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard`
- CRUD routes under `/api/employees`, `/api/tasks`, `/api/attendance`, `/api/business/*`, and `/api/customers`
- `GET /api/health`

