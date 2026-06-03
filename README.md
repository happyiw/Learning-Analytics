# Learning Analytics Platform

## Version

- Backend: `1.3.0`
- Frontend: `1.3.0`

## Current Features

- FastAPI backend with JWT authentication and roles: `student`, `teacher`, `admin`
- Angular frontend with dashboard, profile, courses, analytics, recommendations, lessons, tasks and tests
- Structured lessons with `content_blocks`: text sections, callouts, checklists, tables, charts, stat cards and images
- Open and closed published courses
- Self-enrollment for open courses
- Manual student assignment to closed courses for `teacher` and `admin`
- Personal analytics with progress, topic results, recommendations and test dynamics
- Dedicated Python progress module in [analytics/progress_service.py](analytics/progress_service.py)
- SQLite bootstrap on backend startup for schema synchronization and intro course updates

## Project Structure

- `backend/` — FastAPI app, API routers, models, schemas, bootstrap and backend services
- `frontend/` — Angular application
- `analytics/` — standalone Python analytics helpers
- `app.db` — main SQLite database
- `requirements.txt` — backend dependencies
- `BackendUpdates.md` — current backend change log and API notes

## Dependencies

### Backend

- `fastapi>=0.115,<1.0`
- `uvicorn>=0.30,<1.0`
- `sqlalchemy>=2.0,<3.0`
- `PyJWT>=2.8,<3.0`

### Frontend

- `@angular/common ^21.2.0`
- `@angular/compiler ^21.2.0`
- `@angular/core ^21.2.0`
- `@angular/forms ^21.2.0`
- `@angular/platform-browser ^21.2.0`
- `@angular/router ^21.2.0`
- `rxjs ~7.8.0`
- `tslib ^2.3.0`

## Run Backend

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

API docs:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run Frontend

```powershell
cd frontend
npm install
npm start
```

Frontend URL:

- `http://localhost:4200`

## Run Analytics Module Separately

The analytics helpers are plain Python modules and can be imported independently inside backend services or scripts.

Example:

```powershell
python -c "from analytics.progress_service import ProgressService; print(ProgressService)"
```

## Database Notes

- Backend uses the root `app.db`
- On backend startup the application:
  - creates missing tables
  - adds missing SQLite columns for the current version
  - syncs the intro course and intro test settings
- The intro course is open for enrollment
- The intro test has:
  - unlimited timer
  - one attempt
  - passing score `0`
  - only correct answer options
