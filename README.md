# Employee Audit Manager — Independent Web App

Standalone web product for **Raw Strength Calisthenics — Employee Audit Manager**.

This repository is **independent** of the desktop EXE installer and updater.  
The desktop app (`yalangisexter-ux/audit-report`) remains production fallback and is not modified by this project.

## Features (EXE workflow parity)

- Case-sensitive logins: `Admin` (customer) and `admin` (developer)
- Dashboard KPIs
- Employees, Tasks, Attendance (CRUD)
- Business tracking: products, services, orders, members
- Customer / prospect directory
- Print center summary
- Settings + database status
- Persistent SQLite on Render disk

## Default accounts (bootstrap)

| Username | Role | Password |
|----------|------|----------|
| `Admin` | Customer | `Shiva@01` |
| `admin` | Developer | `kiran123` **or** `Devlopershouse@1996#` |

Usernames are **case-sensitive**.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export AUDIT_DATA_DIR=./data
uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

## Deploy (Render)

1. New Web Service → connect this repo  
2. Or use `render.yaml` Blueprint  
3. Attach a persistent disk at `/var/data`  
4. Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

## API

- `POST /api/auth/login` `{ "username", "password" }`
- `GET  /api/auth/me`
- `GET  /api/dashboard`
- CRUD under `/api/employees`, `/api/tasks`, `/api/attendance`, `/api/business/*`, `/api/customers`
